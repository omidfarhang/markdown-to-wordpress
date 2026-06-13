from __future__ import annotations

import os
from pathlib import Path

from bs4 import BeautifulSoup

from md2wp.config import Settings
from md2wp.logging import get_logger
from md2wp.models import ParseError, Post, PostMetadata
from md2wp.parsers.markdown import parse_date, slug_from_path

logger = get_logger(__name__)


def _select_one(soup: BeautifulSoup, selector: str):
    return soup.select_one(selector)


def _select_all(soup: BeautifulSoup, selector: str):
    return soup.select(selector)


def _extract_categories(soup: BeautifulSoup, settings: Settings) -> list[str]:
    links = _select_all(soup, settings.hugo_build.categories_selector)
    index = settings.hugo_build.category_breadcrumb_index
    if len(links) > index:
        return [links[index].get_text(strip=True)]
    return []


def _extract_tags(soup: BeautifulSoup, settings: Settings) -> list[str]:
    return [el.get_text(strip=True) for el in _select_all(soup, settings.hugo_build.tags_selector)]


def _relative_url(root: Path, build_directory: Path) -> str:
    rel = root.relative_to(build_directory)
    return str(rel).replace("\\", "/")


def _detect_lang_from_html(soup: BeautifulSoup, path: Path) -> str:
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        return html_tag["lang"].split("-")[0].lower()
    match = path.parts
    for part in match:
        if part.endswith(".html") and "." in part:
            suffix = part.rsplit(".", 1)[-1]
            if len(suffix) == 2:
                return suffix.lower()
    return "en"


def parse_hugo_index_html(path: Path, build_directory: Path, settings: Settings) -> Post:
    with path.open(encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    title_el = _select_one(soup, settings.hugo_build.title_selector)
    if not title_el:
        raise ValueError(f"Title not found (selector: {settings.hugo_build.title_selector})")

    date_el = _select_one(soup, settings.hugo_build.date_selector)
    if not date_el:
        raise ValueError(f"Date not found (selector: {settings.hugo_build.date_selector})")

    date_value = date_el.get("title") or date_el.get_text(strip=True)
    content_el = _select_one(soup, settings.hugo_build.content_selector)
    if not content_el:
        raise ValueError(f"Content not found (selector: {settings.hugo_build.content_selector})")

    title = title_el.get_text(strip=True)
    rel_url = _relative_url(path.parent, build_directory)
    slug = slug_from_path(path.parent) if path.parent.name else slug_from_path(path)

    return Post(
        metadata=PostMetadata(
            title=title,
            date=parse_date(date_value),
            slug=slug,
            url=rel_url,
            tags=_extract_tags(soup, settings),
            categories=_extract_categories(soup, settings),
            lang=_detect_lang_from_html(soup, path),
            source_path=path,
        ),
        html_content=str(content_el),
    )


def discover_hugo_build_files(build_directory: Path, settings: Settings) -> list[Path]:
    files: list[Path] = []
    for root, dirs, filenames in os.walk(build_directory):
        root_path = Path(root)
        if settings.hugo_build.filter_year_dirs and root_path == build_directory:
            dirs[:] = [d for d in dirs if d.isdigit() and len(d) == 4]
        if "index.html" in filenames:
            files.append(root_path / "index.html")
    return sorted(files)


def discover_and_parse_hugo_build(
    source: Path, settings: Settings
) -> tuple[list[Post], list[ParseError], list[tuple[Path, str]]]:
    posts: list[Post] = []
    errors: list[ParseError] = []
    skipped: list[tuple[Path, str]] = []

    for path in discover_hugo_build_files(source, settings):
        try:
            posts.append(parse_hugo_index_html(path, source, settings))
        except ValueError as exc:
            errors.append(ParseError(path=path, message=str(exc)))
            logger.error("Failed to parse %s: %s", path, exc)

    return posts, errors, skipped
