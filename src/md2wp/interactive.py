from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import typer

from md2wp.config import Settings


def can_prompt(no_interactive: bool) -> bool:
    """Return True when interactive prompts are allowed."""
    if no_interactive:
        return False
    return sys.stdin.isatty()


def _prompt_source(settings: Settings) -> Settings:
    while True:
        raw = typer.prompt("Source directory")
        path = Path(raw).expanduser()
        if path.is_dir():
            return replace(settings, source=path)
        typer.echo(f"Not a directory: {path}", err=True)


def _prompt_wordpress(settings: Settings) -> Settings:
    url = settings.wordpress_url
    username = settings.wordpress_username
    password = settings.wordpress_password

    if not url:
        url = typer.prompt("WordPress REST API URL")
    if not username:
        username = typer.prompt("WordPress username")
    if not password:
        password = typer.prompt("WordPress application password", hide_input=True)

    return replace(
        settings,
        wordpress_url=url.strip(),
        wordpress_username=username.strip(),
        wordpress_password=password,
    )


def _prompt_export(settings: Settings) -> Settings:
    output = settings.output
    domain = settings.domain

    if not output:
        raw = typer.prompt("WXR output file path")
        output = Path(raw).expanduser()
    if not domain:
        domain = typer.prompt("Site domain (e.g. https://example.com)")

    return replace(settings, output=output, domain=domain.strip())


def prompt_missing_settings(
    settings: Settings,
    *,
    need_wp: bool = False,
    need_export: bool = False,
    no_interactive: bool = False,
) -> Settings:
    """Fill empty required settings via interactive prompts when allowed.

    When prompting is disabled, returns settings unchanged so downstream
    validation can raise the usual ValueError.
    """
    if not can_prompt(no_interactive):
        return settings

    updated = settings

    if not updated.source:
        updated = _prompt_source(updated)

    if need_wp and (
        not updated.wordpress_url
        or not updated.wordpress_username
        or not updated.wordpress_password
    ):
        updated = _prompt_wordpress(updated)

    if need_export and (not updated.output or not updated.domain):
        updated = _prompt_export(updated)

    return updated
