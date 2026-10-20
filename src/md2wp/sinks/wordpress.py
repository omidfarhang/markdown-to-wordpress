from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import requests

from md2wp.config import Settings
from md2wp.logging import get_logger
from md2wp.media import collect_local_images, resolve_featured_path, rewrite_image_srcs
from md2wp.models import ImportResult, Post

logger = get_logger(__name__)

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


class WordPressClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.wordpress_url.rstrip("/")
        self.auth = (settings.wordpress_username, settings.wordpress_password)
        self._tag_cache: dict[str, int] = {}
        self._category_cache: dict[str, int] = {}
        self._media_cache: dict[Path, dict[str, Any]] = {}

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None

        for attempt in range(4):
            try:
                response = requests.request(method, url, auth=self.auth, timeout=60, **kwargs)
            except requests.RequestException as exc:
                last_exc = exc
                if attempt == 3:
                    raise
                time.sleep(2**attempt)
                continue

            if response.status_code not in RETRY_STATUS_CODES or attempt == 3:
                return response

            retry_after = int(response.headers.get("Retry-After", 2**attempt))
            logger.warning(
                "WordPress returned %s, retrying in %ss",
                response.status_code,
                retry_after,
            )
            time.sleep(retry_after)

        raise last_exc or RuntimeError("Request failed")

    def _ensure_auth(self) -> None:
        if not self.base_url:
            raise ValueError("WordPress URL is not configured (MD2WP_WORDPRESS_URL)")
        if not self.settings.wordpress_username or not self.settings.wordpress_password:
            raise ValueError(
                "WordPress credentials are not configured "
                "(MD2WP_WORDPRESS_USERNAME / MD2WP_WORDPRESS_PASSWORD)"
            )

        response = self._request("GET", "/users/me")
        if response.status_code == 401:
            raise ValueError(
                "WordPress authentication failed. Check username and application password."
            )
        if response.status_code >= 400:
            raise ValueError(
                f"WordPress connection failed ({response.status_code}): {response.text[:200]}"
            )

    def _resolve_term(self, endpoint: str, cache: dict[str, int], name: str) -> int:
        key = name.strip().lower()
        if key in cache:
            return cache[key]

        response = self._request("GET", endpoint, params={"search": name, "per_page": 100})
        response.raise_for_status()
        for item in response.json():
            if item.get("name", "").lower() == key:
                cache[key] = item["id"]
                return item["id"]

        response = self._request("POST", endpoint, json={"name": name})
        response.raise_for_status()
        term_id = response.json()["id"]
        cache[key] = term_id
        return term_id

    def _resolve_tags(self, tags: list[str]) -> list[int]:
        return [self._resolve_term("/tags", self._tag_cache, tag) for tag in tags if tag.strip()]

    def _resolve_categories(self, categories: list[str]) -> list[int]:
        return [
            self._resolve_term("/categories", self._category_cache, category)
            for category in categories
            if category.strip()
        ]

    def _find_post_by_slug(self, slug: str) -> dict[str, Any] | None:
        response = self._request("GET", "/posts", params={"slug": slug, "status": "any"})
        response.raise_for_status()
        items = response.json()
        return items[0] if items else None

    def _media_filename_matches(self, item: dict[str, Any], filename: str) -> bool:
        name = filename.lower()
        slug = str(item.get("slug", "")).lower()
        source_url = unquote(str(item.get("source_url", "")))
        url_name = Path(urlparse(source_url).path).name.lower()
        stem = Path(filename).stem.lower()
        return url_name == name or slug == stem or slug == name

    def _find_existing_media(self, path: Path) -> dict[str, Any] | None:
        filename = path.name
        response = self._request("GET", "/media", params={"search": filename, "per_page": 100})
        if response.status_code >= 400:
            logger.warning("Media search failed for %s: %s", filename, response.text[:200])
            return None

        for item in response.json():
            if self._media_filename_matches(item, filename):
                return {"id": item["id"], "source_url": item.get("source_url", "")}
        return None

    def _upload_media(self, path: Path) -> dict[str, Any]:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        with path.open("rb") as handle:
            response = self._request(
                "POST",
                "/media",
                headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
                files={"file": (path.name, handle, content_type)},
            )

        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"Failed to upload media '{path.name}' "
                f"({response.status_code}): {response.text[:300]}"
            )

        data = response.json()
        return {"id": data["id"], "source_url": data.get("source_url", "")}

    def ensure_media(self, path: Path) -> dict[str, Any]:
        """Upload or reuse media for an absolute path; cache by path."""
        resolved = path.resolve()
        if resolved in self._media_cache:
            return self._media_cache[resolved]

        existing = self._find_existing_media(resolved)
        if existing:
            logger.debug("Reusing media %s for %s", existing["id"], resolved.name)
            self._media_cache[resolved] = existing
            return existing

        uploaded = self._upload_media(resolved)
        logger.info("Uploaded media: %s → %s", resolved.name, uploaded["source_url"])
        self._media_cache[resolved] = uploaded
        return uploaded

    def _prepare_post_media(self, post: Post) -> tuple[str, int | None]:
        """Upload local images, rewrite HTML srcs, return (html, featured_media_id)."""
        base_dir = post.metadata.source_path.parent if post.metadata.source_path else Path(".")
        html = post.html_content
        src_map: dict[str, str] = {}
        path_to_media: dict[Path, dict[str, Any]] = {}

        for original_src, abs_path in collect_local_images(html, base_dir):
            media = self.ensure_media(abs_path)
            src_map[original_src] = media["source_url"]
            path_to_media[abs_path.resolve()] = media

        featured_id: int | None = None
        featured_path = resolve_featured_path(post.metadata.featured_image, base_dir)
        if featured_path:
            media = path_to_media.get(featured_path.resolve())
            if media is None:
                media = self.ensure_media(featured_path)
            featured_id = media["id"]

        html = rewrite_image_srcs(html, src_map)
        return html, featured_id

    def _build_payload(
        self, post: Post, html_content: str, featured_media: int | None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": post.metadata.title,
            "content": html_content,
            "status": self.settings.status.value,
            "slug": post.metadata.slug,
            "date": post.metadata.date.isoformat(),
        }
        if post.metadata.excerpt:
            payload["excerpt"] = post.metadata.excerpt
        if featured_media is not None:
            payload["featured_media"] = featured_media

        tag_ids = self._resolve_tags(post.metadata.tags)
        category_ids = self._resolve_categories(post.metadata.categories)
        if tag_ids:
            payload["tags"] = tag_ids
        if category_ids:
            payload["categories"] = category_ids

        return payload

    def _set_post_meta(self, post_id: int, key: str, value: str) -> None:
        response = self._request(
            "POST", f"/posts/{post_id}/meta", json={"key": key, "value": value}
        )
        if response.status_code >= 400:
            logger.warning(
                "Failed to set meta %s on post %s: %s", key, post_id, response.text[:200]
            )

    def publish_post(self, post: Post) -> tuple[str, int]:
        html_content, featured_media = self._prepare_post_media(post)
        payload = self._build_payload(post, html_content, featured_media)
        existing = self._find_post_by_slug(post.metadata.slug)

        if existing:
            post_id = existing["id"]
            response = self._request("PUT", f"/posts/{post_id}", json=payload)
            action = "updated"
        else:
            response = self._request("POST", "/posts", json=payload)
            action = "created"
            post_id = response.json().get("id") if response.ok else 0

        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"Failed to {action} post '{post.metadata.title}' "
                f"({response.status_code}): {response.text[:300]}"
            )

        if post_id:
            if post.metadata.shortlink:
                self._set_post_meta(post_id, "shortlink", post.metadata.shortlink)
            if post.metadata.lang:
                self._set_post_meta(post_id, "lang", post.metadata.lang)

        return action, post_id


def publish_to_wordpress(posts: list[Post], settings: Settings) -> ImportResult:
    client = WordPressClient(settings)
    client._ensure_auth()

    result = ImportResult(posts=posts, dry_run=False)
    for post in posts:
        try:
            action, _ = client.publish_post(post)
            if action == "updated":
                result.updated += 1
                logger.info("Updated: %s", post.metadata.title)
            else:
                result.published += 1
                logger.info("Published: %s", post.metadata.title)
        except Exception as exc:
            result.failed += 1
            path = post.metadata.source_path or post.metadata.slug
            logger.error("Failed to publish %s: %s", path, exc)

    return result
