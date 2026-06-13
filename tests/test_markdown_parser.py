from pathlib import Path

from md2wp.config import Settings
from md2wp.parsers.markdown import (
    discover_and_parse_markdown,
    parse_date,
    slug_from_url,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_slug_from_url():
    assert slug_from_url("2024/08/13/my-post/") == "my-post"


def test_parse_date_iso():
    dt = parse_date("2024-08-13T16:42:19+03:30")
    assert dt.year == 2024
    assert dt.month == 8


def test_parse_date_rfc2822():
    dt = parse_date("Mon, 12 Jun 2023 20:40:00 +0000")
    assert dt.year == 2023
    assert dt.month == 6


def test_parse_markdown_file():
    settings = Settings(recursive=False, include_drafts=False)
    posts, errors, skipped = discover_and_parse_markdown(FIXTURES, settings)
    assert not errors
    assert len(posts) == 1
    post = posts[0]
    assert post.metadata.title.startswith("The Hidden World")
    assert "Brainfuck" in post.metadata.tags
    assert "TechBlog" in post.metadata.categories
    assert post.metadata.lang == "en"
    assert "---" not in post.html_content
    assert "<h2>" in post.html_content
    assert "horizontal rule" in post.html_content


def test_skips_drafts_by_default():
    settings = Settings(recursive=False, include_drafts=False)
    posts, errors, skipped = discover_and_parse_markdown(FIXTURES, settings)
    assert all("Draft Post" not in p.metadata.title for p in posts)
    assert any(reason == "draft" for _, reason in skipped)


def test_includes_drafts_when_requested():
    settings = Settings(recursive=False, include_drafts=True)
    posts, errors, skipped = discover_and_parse_markdown(FIXTURES, settings)
    assert any(p.metadata.title == "Draft Post" for p in posts)
