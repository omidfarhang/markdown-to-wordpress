from __future__ import annotations

import json
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from md2wp.config import ImportMode, PostStatus, load_settings, settings_as_dict
from md2wp.logging import setup_logging
from md2wp.pipeline import run_export, run_import, run_validate

app = typer.Typer(
    name="md2wp",
    help="Import Markdown or Hugo build output into WordPress.",
    no_args_is_help=True,
)


class ModeOption(str, Enum):
    markdown = "markdown"
    hugo_build = "hugo-build"


class StatusOption(str, Enum):
    draft = "draft"
    publish = "publish"
    private = "private"


def _build_settings(
    config: Path | None,
    mode: ModeOption | None,
    source: Path | None,
    output: Path | None,
    domain: str | None,
    status: StatusOption | None,
    recursive: bool | None,
    include_drafts: bool | None,
    dry_run: bool,
    verbose: bool,
):
    import_mode = None
    if mode == ModeOption.markdown:
        import_mode = ImportMode.MARKDOWN
    elif mode == ModeOption.hugo_build:
        import_mode = ImportMode.HUGO_BUILD

    post_status = PostStatus(status.value) if status else None

    return load_settings(
        config_path=config,
        mode=import_mode,
        source=source,
        output=output,
        domain=domain,
        status=post_status,
        recursive=recursive,
        include_drafts=include_drafts,
        dry_run=dry_run,
        verbose=verbose,
    )


def _exit_code(result) -> int:
    if result.errors or result.failed:
        return 1
    return 0


@app.command("import")
def import_cmd(
    source: Annotated[
        Path | None, typer.Option("--source", "-s", help="Input directory")
    ] = None,
    mode: Annotated[
        ModeOption | None, typer.Option("--mode", "-m", help="Import mode")
    ] = None,
    status: Annotated[
        StatusOption | None, typer.Option("--status", help="WordPress post status")
    ] = None,
    recursive: Annotated[
        bool | None, typer.Option("--recursive/--no-recursive", help="Scan subdirectories")
    ] = None,
    include_drafts: Annotated[
        bool, typer.Option("--include-drafts", help="Include draft posts")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Parse only, do not publish")
    ] = False,
    config: Annotated[
        Path | None, typer.Option("--config", "-c", help="Path to md2wp.toml")
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose logging")] = False,
) -> None:
    """Import posts to WordPress via REST API."""
    settings = _build_settings(
        config=config,
        mode=mode,
        source=source,
        output=None,
        domain=None,
        status=status,
        recursive=recursive,
        include_drafts=include_drafts,
        dry_run=dry_run,
        verbose=verbose,
    )
    setup_logging(settings.verbose)

    try:
        result = run_import(settings)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"Done: {result.published} published, {result.updated} updated, "
        f"{result.failed} failed, {len(result.errors)} parse errors, "
        f"{len(result.skipped)} skipped"
    )
    raise typer.Exit(code=_exit_code(result))


@app.command("export")
def export_cmd(
    source: Annotated[
        Path | None, typer.Option("--source", "-s", help="Input directory")
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="WXR output file path")
    ] = None,
    domain: Annotated[
        str | None, typer.Option("--domain", help="Site domain for WXR links")
    ] = None,
    mode: Annotated[
        ModeOption | None, typer.Option("--mode", "-m", help="Import mode")
    ] = None,
    status: Annotated[
        StatusOption | None, typer.Option("--status", help="Post status in WXR")
    ] = None,
    recursive: Annotated[
        bool | None, typer.Option("--recursive/--no-recursive", help="Scan subdirectories")
    ] = None,
    include_drafts: Annotated[
        bool, typer.Option("--include-drafts", help="Include draft posts")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Parse only, do not write WXR")
    ] = False,
    config: Annotated[
        Path | None, typer.Option("--config", "-c", help="Path to md2wp.toml")
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose logging")] = False,
) -> None:
    """Export posts to WordPress WXR format."""
    settings = _build_settings(
        config=config,
        mode=mode,
        source=source,
        output=output,
        domain=domain,
        status=status,
        recursive=recursive,
        include_drafts=include_drafts,
        dry_run=dry_run,
        verbose=verbose,
    )
    setup_logging(settings.verbose)

    try:
        result = run_export(settings)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if result.export_path:
        typer.echo(f"Exported to {result.export_path}")
    else:
        typer.echo(
            f"Validated {len(result.posts)} posts "
            f"({len(result.errors)} errors, {len(result.skipped)} skipped)"
        )
    raise typer.Exit(code=_exit_code(result))


@app.command("validate")
def validate_cmd(
    source: Annotated[
        Path | None, typer.Option("--source", "-s", help="Input directory")
    ] = None,
    mode: Annotated[
        ModeOption | None, typer.Option("--mode", "-m", help="Import mode")
    ] = None,
    recursive: Annotated[
        bool | None, typer.Option("--recursive/--no-recursive", help="Scan subdirectories")
    ] = None,
    include_drafts: Annotated[
        bool, typer.Option("--include-drafts", help="Include draft posts")
    ] = False,
    config: Annotated[
        Path | None, typer.Option("--config", "-c", help="Path to md2wp.toml")
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose logging")] = False,
) -> None:
    """Validate source files without importing or exporting."""
    settings = _build_settings(
        config=config,
        mode=mode,
        source=source,
        output=None,
        domain=None,
        status=None,
        recursive=recursive,
        include_drafts=include_drafts,
        dry_run=True,
        verbose=verbose,
    )
    setup_logging(settings.verbose)

    try:
        result = run_validate(settings)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    for post in result.posts:
        typer.echo(f"OK  {post.metadata.source_path} -> {post.metadata.slug}")
    for error in result.errors:
        typer.echo(f"ERR {error.path}: {error.message}", err=True)
    for path, reason in result.skipped:
        typer.echo(f"SKIP {path} ({reason})")

    typer.echo(
        f"\nSummary: {len(result.posts)} valid, {len(result.errors)} errors, "
        f"{len(result.skipped)} skipped"
    )
    raise typer.Exit(code=_exit_code(result))


config_app = typer.Typer(help="Configuration commands.")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show(
    config: Annotated[
        Path | None, typer.Option("--config", "-c", help="Path to md2wp.toml")
    ] = None,
) -> None:
    """Show effective configuration."""
    settings = load_settings(config_path=config)
    json.dump(settings_as_dict(settings), sys.stdout, indent=2)
    sys.stdout.write("\n")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
