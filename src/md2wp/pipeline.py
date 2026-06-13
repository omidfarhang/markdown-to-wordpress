from __future__ import annotations

from md2wp.config import ImportMode, Settings
from md2wp.logging import get_logger
from md2wp.models import ImportResult
from md2wp.parsers.hugo_build import discover_and_parse_hugo_build
from md2wp.parsers.markdown import discover_and_parse_markdown
from md2wp.sinks.wordpress import publish_to_wordpress
from md2wp.sinks.wxr import export_to_wxr

logger = get_logger(__name__)


def _ensure_source(settings: Settings) -> None:
    if not settings.source:
        raise ValueError("Source directory is required (--source or import.source in config)")
    if not settings.source.is_dir():
        raise ValueError(f"Source directory does not exist: {settings.source}")


def discover_and_parse(settings: Settings) -> ImportResult:
    _ensure_source(settings)

    if settings.mode == ImportMode.HUGO_BUILD:
        posts, errors, skipped = discover_and_parse_hugo_build(settings.source, settings)
    else:
        posts, errors, skipped = discover_and_parse_markdown(settings.source, settings)

    logger.info(
        "Discovered %d posts (%d errors, %d skipped)",
        len(posts),
        len(errors),
        len(skipped),
    )

    return ImportResult(posts=posts, errors=errors, skipped=skipped, dry_run=settings.dry_run)


def run_import(settings: Settings) -> ImportResult:
    result = discover_and_parse(settings)

    if settings.dry_run:
        logger.info("Dry run: would process %d posts", len(result.posts))
        for post in result.posts:
            logger.info(
                "  - %s (%s, slug=%s)",
                post.metadata.title,
                post.metadata.date.date(),
                post.metadata.slug,
            )
        return result

    if not result.posts:
        logger.warning("No posts to import")
        return result

    publish_result = publish_to_wordpress(result.posts, settings)
    publish_result.errors = result.errors
    publish_result.skipped = result.skipped
    return publish_result


def run_export(settings: Settings) -> ImportResult:
    result = discover_and_parse(settings)

    if settings.dry_run:
        logger.info("Dry run: would export %d posts", len(result.posts))
        return result

    if not result.posts:
        logger.warning("No posts to export")
        result.errors = result.errors
        return result

    export_result = export_to_wxr(result.posts, settings)
    export_result.errors = result.errors
    export_result.skipped = result.skipped
    return export_result


def run_validate(settings: Settings) -> ImportResult:
    return discover_and_parse(settings)
