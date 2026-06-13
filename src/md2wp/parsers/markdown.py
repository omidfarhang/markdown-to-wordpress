from __future__ import annotations

import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import frontmatter
import markdown

from md2wp.config import Settings
from md2wp.logging import get_logger
from md2wp.models import ParseError, Post, PostMetadata

logger = get_logger(__name__)

LANG_SUFFIX_RE = re.compile(r"\.([a-z]{2})\.md$", re.IGNORECASE)


def slug_from_url(url: str) -> str:
    parts = url.strip("/").split("/")
    return parts[-1] if parts else ""


def slug_from_path(path: Path) -> str:
    name = path.stem
    match = LANG_SUFFIX_RE.search(path.name)
    if match:
        name = name[: -(len(match.group(1)) + 1)]
    return name


def parse_date(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if value is None:
        raise ValueError("Date is missing")

    text = str(value).strip()
    if not text:
        raise ValueError("Date is empty")

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass

    try:
        return parsedate_to_datetime(text)
    except (TypeError, ValueError):
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%b %d, %Y %I:%M %p %Z",
        "%b %d, %Y %I:%M %p %z",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unsupported date format: {text!r}")


def detect_lang(path: Path, metadata: dict[str, Any]) -> str:
    if metadata.get("lang"):
        return str(metadata["lang"])
    match = LANG_SUFFIX_RE.search(path.name)
    if match:
        return match.group(1).lower()
    return "en"


def should_skip_file(path: Path, metadata: dict[str, Any], settings: Settings) -> str | None:
    if path.name == "_index.md":
        return "index file"
    if path.name.startswith("."):
        return "hidden file"
    if metadata.get("draft") and not settings.include_drafts:
        return "draft"
    return None


def discover_markdown_files(source: Path, recursive: bool) -> list[Path]:
    pattern = "**/*.md" if recursive else "*.md"
    return sorted(source.glob(pattern))


def parse_markdown_file(path: Path, settings: Settings) -> Post | None:
    post = frontmatter.load(path)
    metadata = dict(post.metadata)
    skip_reason = should_skip_file(path, metadata, settings)
    if skip_reason:
        raise ValueError(skip_reason)

    title = metadata.get("title")
    if not title:
        raise ValueError("Missing required field: title")

    date_raw = metadata.get("date")
    if not date_raw:
        raise ValueError("Missing required field: date")

    url = str(metadata.get("url", "")).strip()
    slug = metadata.get("slug") or (slug_from_url(url) if url else slug_from_path(path))

    tags = metadata.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    categories = metadata.get("categories") or []
    if isinstance(categories, str):
        categories = [categories]

    html_content = markdown.markdown(
        post.content,
        extensions=settings.markdown_extensions,
    )

    if not html_content.strip():
        logger.warning("Empty content body in %s", path)

    return Post(
        metadata=PostMetadata(
            title=str(title),
            date=parse_date(date_raw),
            slug=str(slug),
            url=url,
            tags=[str(t) for t in tags],
            categories=[str(c) for c in categories],
            lang=detect_lang(path, metadata),
            excerpt=str(metadata.get("excerpt", "")),
            shortlink=str(metadata.get("shortlink", "")),
            draft=bool(metadata.get("draft", False)),
            source_path=path,
            extra={
                k: v
                for k, v in metadata.items()
                if k
                not in {
                    "title",
                    "date",
                    "slug",
                    "url",
                    "tags",
                    "categories",
                    "lang",
                    "excerpt",
                    "shortlink",
                    "draft",
                }
            },
        ),
        html_content=html_content,
    )


def discover_and_parse_markdown(
    source: Path, settings: Settings
) -> tuple[list[Post], list[ParseError], list[tuple[Path, str]]]:
    posts: list[Post] = []
    errors: list[ParseError] = []
    skipped: list[tuple[Path, str]] = []

    for path in discover_markdown_files(source, settings.recursive):
        try:
            post = parse_markdown_file(path, settings)
            if post:
                posts.append(post)
        except ValueError as exc:
            message = str(exc)
            if message in {"index file", "hidden file", "draft"}:
                skipped.append((path, message))
                logger.debug("Skipped %s (%s)", path, message)
            else:
                errors.append(ParseError(path=path, message=message))
                logger.error("Failed to parse %s: %s", path, message)

    return posts, errors, skipped
