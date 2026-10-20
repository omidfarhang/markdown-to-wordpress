from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from md2wp.logging import get_logger

logger = get_logger(__name__)


def _is_remote_or_data(src: str) -> bool:
    lowered = src.strip().lower()
    return (
        lowered.startswith("http://")
        or lowered.startswith("https://")
        or lowered.startswith("data:")
        or lowered.startswith("//")
    )


def resolve_local_path(src: str, base_dir: Path) -> Path | None:
    """Resolve a local image src against base_dir. Returns None if remote/data."""
    if not src or _is_remote_or_data(src):
        return None

    parsed = urlparse(src)
    path_part = unquote(parsed.path)
    if not path_part:
        return None

    candidate = Path(path_part)
    if not candidate.is_absolute():
        candidate = (base_dir / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


def collect_local_images(html: str, base_dir: Path) -> list[tuple[str, Path]]:
    """
    Collect local img[src] from HTML, resolved against base_dir.

    Returns (original_src, absolute_path) pairs for files that exist.
    Missing files are logged as warnings and omitted (src left unchanged by callers).
    """
    soup = BeautifulSoup(html, "html.parser")
    found: list[tuple[str, Path]] = []
    seen: set[str] = set()

    for img in soup.find_all("img"):
        src = img.get("src")
        if not src or src in seen:
            continue
        seen.add(src)

        resolved = resolve_local_path(src, base_dir)
        if resolved is None:
            continue

        if not resolved.is_file():
            logger.warning("Local image not found (leaving src unchanged): %s", src)
            continue

        found.append((src, resolved))

    return found


def rewrite_image_srcs(html: str, src_map: dict[str, str]) -> str:
    """Rewrite img[src] values using src_map (original src → new URL)."""
    if not src_map:
        return html

    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src")
        if src and src in src_map:
            img["src"] = src_map[src]
    return str(soup)


def resolve_featured_path(featured_image: str | None, base_dir: Path) -> Path | None:
    """Resolve featured_image frontmatter path; warn and return None if missing."""
    if not featured_image:
        return None

    resolved = resolve_local_path(featured_image, base_dir)
    if resolved is None:
        return None

    if not resolved.is_file():
        logger.warning("Featured image not found: %s", featured_image)
        return None

    return resolved
