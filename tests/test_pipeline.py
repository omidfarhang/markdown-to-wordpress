from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from md2wp.config import ImportMode, Settings
from md2wp.models import Post, PostMetadata
from md2wp.pipeline import discover_and_parse, run_export, run_import

FIXTURES = Path(__file__).parent / "fixtures"


def _sample_post() -> Post:
    return Post(
        metadata=PostMetadata(
            title="Sample",
            date=datetime(2024, 1, 1),
            slug="sample",
        ),
        html_content="<p>hi</p>",
    )


def test_discover_markdown_mode():
    settings = Settings(mode=ImportMode.MARKDOWN, source=FIXTURES, recursive=False)
    result = discover_and_parse(settings)
    assert result.posts
    assert not result.errors


def test_discover_hugo_build_mode_branch(monkeypatch):
    settings = Settings(mode=ImportMode.HUGO_BUILD, source=FIXTURES)
    called = {}

    def fake_hugo(source, settings):
        called["ok"] = True
        return [_sample_post()], [], []

    monkeypatch.setattr(
        "md2wp.pipeline.discover_and_parse_hugo_build",
        fake_hugo,
    )
    monkeypatch.setattr(
        "md2wp.pipeline.discover_and_parse_markdown",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("markdown path called")),
    )

    result = discover_and_parse(settings)

    assert called["ok"]
    assert len(result.posts) == 1


def test_missing_source_raises():
    settings = Settings(source=None)
    with pytest.raises(ValueError, match="Source directory is required"):
        discover_and_parse(settings)


def test_missing_source_dir_raises(tmp_path):
    settings = Settings(source=tmp_path / "does-not-exist")
    with pytest.raises(ValueError, match="does not exist"):
        discover_and_parse(settings)


def test_import_dry_run_skips_wordpress(monkeypatch):
    settings = Settings(
        mode=ImportMode.MARKDOWN,
        source=FIXTURES,
        recursive=False,
        dry_run=True,
    )
    publish = MagicMock()
    monkeypatch.setattr("md2wp.pipeline.publish_to_wordpress", publish)

    result = run_import(settings)

    assert result.dry_run is True
    assert result.posts
    publish.assert_not_called()


def test_export_dry_run_skips_wxr(monkeypatch, tmp_path):
    settings = Settings(
        mode=ImportMode.MARKDOWN,
        source=FIXTURES,
        recursive=False,
        dry_run=True,
        output=tmp_path / "out.xml",
        domain="https://example.com",
    )
    export = MagicMock()
    monkeypatch.setattr("md2wp.pipeline.export_to_wxr", export)

    result = run_export(settings)

    assert result.dry_run is True
    assert result.posts
    export.assert_not_called()
