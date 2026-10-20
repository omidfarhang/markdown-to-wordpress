from pathlib import Path

from md2wp.config import Settings
from md2wp.interactive import can_prompt, prompt_missing_settings


def test_can_prompt_respects_no_interactive(monkeypatch):
    monkeypatch.setattr("md2wp.interactive.sys.stdin.isatty", lambda: True)
    assert can_prompt(no_interactive=False) is True
    assert can_prompt(no_interactive=True) is False


def test_can_prompt_false_when_not_tty(monkeypatch):
    monkeypatch.setattr("md2wp.interactive.sys.stdin.isatty", lambda: False)
    assert can_prompt(no_interactive=False) is False


def test_prompt_missing_source(tmp_path, monkeypatch):
    monkeypatch.setattr("md2wp.interactive.can_prompt", lambda no_interactive: True)
    monkeypatch.setattr(
        "md2wp.interactive.typer.prompt",
        lambda *args, **kwargs: str(tmp_path),
    )

    settings = prompt_missing_settings(Settings(), no_interactive=False)
    assert settings.source == tmp_path


def test_prompt_missing_wordpress(monkeypatch):
    monkeypatch.setattr("md2wp.interactive.can_prompt", lambda no_interactive: True)
    answers = iter(
        [
            "https://example.com/wp-json/wp/v2",
            "admin",
            "secret-pass",
        ]
    )
    monkeypatch.setattr(
        "md2wp.interactive.typer.prompt",
        lambda *args, **kwargs: next(answers),
    )

    settings = prompt_missing_settings(
        Settings(source=Path("/posts")),
        need_wp=True,
        no_interactive=False,
    )
    assert settings.wordpress_url == "https://example.com/wp-json/wp/v2"
    assert settings.wordpress_username == "admin"
    assert settings.wordpress_password == "secret-pass"


def test_prompt_missing_export(tmp_path, monkeypatch):
    monkeypatch.setattr("md2wp.interactive.can_prompt", lambda no_interactive: True)
    out = tmp_path / "export.xml"
    answers = iter([str(out), "https://example.com"])
    monkeypatch.setattr(
        "md2wp.interactive.typer.prompt",
        lambda *args, **kwargs: next(answers),
    )

    settings = prompt_missing_settings(
        Settings(source=tmp_path),
        need_export=True,
        no_interactive=False,
    )
    assert settings.output == out
    assert settings.domain == "https://example.com"


def test_prompt_skipped_when_disabled(monkeypatch):
    monkeypatch.setattr("md2wp.interactive.can_prompt", lambda no_interactive: False)
    called = []

    def fake_prompt(*args, **kwargs):
        called.append(True)
        return "x"

    monkeypatch.setattr("md2wp.interactive.typer.prompt", fake_prompt)

    settings = prompt_missing_settings(
        Settings(),
        need_wp=True,
        need_export=True,
        no_interactive=True,
    )
    assert settings.source is None
    assert not called
