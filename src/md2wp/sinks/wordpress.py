from __future__ import annotations

import time
from typing import Any

import requests

from md2wp.config import Settings
from md2wp.logging import get_logger
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

    def _build_payload(self, post: Post) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": post.metadata.title,
            "content": post.html_content,
            "status": self.settings.status.value,
            "slug": post.metadata.slug,
            "date": post.metadata.date.isoformat(),
        }
        if post.metadata.excerpt:
            payload["excerpt"] = post.metadata.excerpt

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
        payload = self._build_payload(post)
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
