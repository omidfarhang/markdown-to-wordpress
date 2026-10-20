from pathlib import Path

from typer.testing import CliRunner

from md2wp.cli import app

runner = CliRunner()
FIXTURES = Path(__file__).parent / "fixtures"


def _clear_source_env(monkeypatch):
    for key in (
        "MD2WP_SOURCE",
        "MARKDOWN_DIRECTORY",
        "HUGO_BUILD_DIRECTORY",
        "MD2WP_WORDPRESS_URL",
        "MD2WP_WORDPRESS_USERNAME",
        "MD2WP_WORDPRESS_PASSWORD",
        "WORDPRESS_URL",
        "USERNAME",
        "PASSWORD",
        "MD2WP_EXPORT_OUTPUT",
        "EXPORT_DIRECTORY",
        "DOMAIN",
    ):
        monkeypatch.delenv(key, raising=False)


def test_validate_command():
    result = runner.invoke(app, ["validate", "-s", str(FIXTURES)])
    assert result.exit_code == 0
    assert "OK" in result.stdout
    assert "Summary:" in result.stdout


def test_import_dry_run():
    result = runner.invoke(
        app,
        ["import", "-s", str(FIXTURES), "--dry-run"],
    )
    assert result.exit_code == 0
    assert "Done:" in result.stdout


def test_export_dry_run():
    result = runner.invoke(
        app,
        [
            "export",
            "-s",
            str(FIXTURES),
            "--dry-run",
            "--domain",
            "https://example.com",
            "-o",
            "/tmp/test-export.xml",
        ],
    )
    assert result.exit_code == 0
    assert "Validated" in result.stdout


def test_config_show():
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert '"mode"' in result.stdout


def test_validate_prompts_for_source(monkeypatch):
    _clear_source_env(monkeypatch)
    monkeypatch.setattr(
        "md2wp.interactive.can_prompt",
        lambda no_interactive: not no_interactive,
    )
    result = runner.invoke(app, ["validate"], input=f"{FIXTURES}\n")
    assert result.exit_code == 0
    assert "Summary:" in result.stdout


def test_validate_no_interactive_requires_source(monkeypatch):
    _clear_source_env(monkeypatch)
    result = runner.invoke(app, ["validate", "--no-interactive"])
    assert result.exit_code == 1
    assert "Source directory is required" in result.output
