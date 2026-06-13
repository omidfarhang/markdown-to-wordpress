from pathlib import Path

from typer.testing import CliRunner

from md2wp.cli import app

runner = CliRunner()
FIXTURES = Path(__file__).parent / "fixtures"


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
