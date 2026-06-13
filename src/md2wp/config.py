from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib

from dotenv import load_dotenv


class ImportMode(str, Enum):
    MARKDOWN = "markdown"
    HUGO_BUILD = "hugo-build"


class PostStatus(str, Enum):
    DRAFT = "draft"
    PUBLISH = "publish"
    PRIVATE = "private"


@dataclass
class HugoBuildSelectors:
    title_selector: str = "h1.post-title"
    date_selector: str = "div.post-meta span[title]"
    content_selector: str = "div.post-content"
    tags_selector: str = "ul.post-tags a"
    categories_selector: str = "div.breadcrumbs a"
    category_breadcrumb_index: int = 2
    filter_year_dirs: bool = True


@dataclass
class Settings:
    mode: ImportMode = ImportMode.MARKDOWN
    source: Path | None = None
    output: Path | None = None
    domain: str = ""
    status: PostStatus = PostStatus.DRAFT
    recursive: bool = True
    include_drafts: bool = False
    dry_run: bool = False
    verbose: bool = False
    config_path: Path | None = None

    wordpress_url: str = ""
    wordpress_username: str = ""
    wordpress_password: str = ""

    site_title: str = "Imported Site"
    site_description: str = "Posts imported by md2wp"
    site_language: str = "en"

    hugo_build: HugoBuildSelectors = field(default_factory=HugoBuildSelectors)

    markdown_extensions: list[str] = field(
        default_factory=lambda: ["fenced_code", "tables", "nl2br"]
    )


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _legacy_env(key: str, new_key: str, default: str = "") -> str:
    return _env(new_key) or _env(key, default)


def load_settings(
    *,
    config_path: Path | None = None,
    mode: ImportMode | None = None,
    source: Path | None = None,
    output: Path | None = None,
    domain: str | None = None,
    status: PostStatus | None = None,
    recursive: bool | None = None,
    include_drafts: bool | None = None,
    dry_run: bool | None = None,
    verbose: bool | None = None,
) -> Settings:
    load_dotenv()

    resolved_config = config_path
    if resolved_config is None:
        for candidate in (Path("md2wp.toml"), Path(".md2wp.toml")):
            if candidate.is_file():
                resolved_config = candidate
                break

    toml_data = _load_toml(resolved_config) if resolved_config else {}
    wp = toml_data.get("wordpress", {})
    imp = toml_data.get("import", {})
    site = toml_data.get("site", {})
    hb = toml_data.get("hugo_build", {})

    def pick(cli_val, toml_val, env_val, default):
        if cli_val is not None:
            return cli_val
        if toml_val not in (None, ""):
            return toml_val
        if env_val not in (None, ""):
            return env_val
        return default

    mode_str = pick(
        mode.value if mode else None,
        imp.get("mode"),
        _legacy_env("MARKDOWN_PARSER", "MD2WP_MODE"),
        ImportMode.MARKDOWN.value,
    )
    if mode_str == "hugo_build":
        mode_str = ImportMode.HUGO_BUILD.value
    elif mode_str == "normal":
        mode_str = ImportMode.MARKDOWN.value

    source_str = pick(
        str(source) if source else None,
        imp.get("source"),
        _legacy_env("MARKDOWN_DIRECTORY", "MD2WP_SOURCE")
        or _legacy_env("HUGO_BUILD_DIRECTORY", "MD2WP_HUGO_BUILD_SOURCE"),
        "",
    )

    status_str = pick(
        status.value if status else None,
        imp.get("status"),
        _env("MD2WP_STATUS"),
        PostStatus.DRAFT.value,
    )

    settings = Settings(
        mode=ImportMode(mode_str),
        source=Path(source_str).expanduser() if source_str else None,
        output=Path(output).expanduser()
        if output
        else Path(imp.get("output", _env("EXPORT_DIRECTORY", ""))).expanduser()
        if (output or imp.get("output") or _env("EXPORT_DIRECTORY"))
        else None,
        domain=pick(domain, imp.get("domain") or site.get("domain"), _env("DOMAIN"), ""),
        status=PostStatus(status_str),
        recursive=pick(recursive, imp.get("recursive"), None, True),
        include_drafts=pick(include_drafts, imp.get("include_drafts"), None, False),
        dry_run=pick(dry_run, imp.get("dry_run"), None, False),
        verbose=pick(verbose, imp.get("verbose"), None, False),
        config_path=resolved_config,
        wordpress_url=pick(
            None,
            wp.get("url"),
            _legacy_env("WORDPRESS_URL", "MD2WP_WORDPRESS_URL"),
            "",
        ),
        wordpress_username=pick(
            None,
            wp.get("username"),
            _legacy_env("USERNAME", "MD2WP_WORDPRESS_USERNAME"),
            "",
        ),
        wordpress_password=pick(
            None,
            None,
            _legacy_env("PASSWORD", "MD2WP_WORDPRESS_PASSWORD"),
            "",
        ),
        site_title=site.get("title", "Imported Site"),
        site_description=site.get("description", "Posts imported by md2wp"),
        site_language=site.get("language", "en"),
        hugo_build=HugoBuildSelectors(
            title_selector=hb.get("title_selector", HugoBuildSelectors.title_selector),
            date_selector=hb.get("date_selector", HugoBuildSelectors.date_selector),
            content_selector=hb.get("content_selector", HugoBuildSelectors.content_selector),
            tags_selector=hb.get("tags_selector", HugoBuildSelectors.tags_selector),
            categories_selector=hb.get(
                "categories_selector", HugoBuildSelectors.categories_selector
            ),
            category_breadcrumb_index=hb.get(
                "category_breadcrumb_index", HugoBuildSelectors.category_breadcrumb_index
            ),
            filter_year_dirs=hb.get("filter_year_dirs", True),
        ),
    )

    return settings


def settings_as_dict(settings: Settings) -> dict[str, Any]:
    return {
        "mode": settings.mode.value,
        "source": str(settings.source) if settings.source else None,
        "output": str(settings.output) if settings.output else None,
        "domain": settings.domain or None,
        "status": settings.status.value,
        "recursive": settings.recursive,
        "include_drafts": settings.include_drafts,
        "dry_run": settings.dry_run,
        "config_path": str(settings.config_path) if settings.config_path else None,
        "wordpress_url": settings.wordpress_url or None,
        "wordpress_username": settings.wordpress_username or None,
        "wordpress_password": "***" if settings.wordpress_password else None,
        "site_title": settings.site_title,
        "hugo_build": {
            "title_selector": settings.hugo_build.title_selector,
            "date_selector": settings.hugo_build.date_selector,
            "content_selector": settings.hugo_build.content_selector,
        },
    }
