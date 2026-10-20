from pathlib import Path

from md2wp.config import Settings
from md2wp.parsers.markdown import (
    detect_translation_key,
    discover_and_parse_markdown,
    parse_date,
    parse_markdown_file,
    slug_from_url,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_slug_from_url():
    assert slug_from_url("2024/08/13/my-post/") == "my-post"


def test_detect_translation_key_from_lang_suffix():
    assert detect_translation_key(Path("post.en.md"), {}) == "post"
    assert detect_translation_key(Path("my-article.fr.md"), {}) == "my-article"


def test_detect_translation_key_from_frontmatter():
    assert (
        detect_translation_key(Path("post.en.md"), {"translation_key": "shared-id"})
        == "shared-id"
    )
    assert (
        detect_translation_key(Path("post.md"), {"translation_of": "parent-slug"})
        == "parent-slug"
    )
    assert (
        detect_translation_key(Path("post.md"), {"translations_key": "group-a"})
        == "group-a"
    )


def test_detect_translation_key_empty_without_suffix_or_frontmatter():
    assert detect_translation_key(Path("post.md"), {}) == ""


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
    assert post.metadata.translation_key == "sample-post"
    assert "---" not in post.html_content
    assert "<h2>" in post.html_content
    assert "horizontal rule" in post.html_content


def test_parse_translation_key_from_frontmatter(tmp_path: Path):
    path = tmp_path / "plain.md"
    path.write_text(
        "---\n"
        "title: Linked Post\n"
        "date: 2024-01-01\n"
        "translation_key: my-group\n"
        "---\n"
        "Body\n",
        encoding="utf-8",
    )
    post = parse_markdown_file(path, Settings())
    assert post.metadata.translation_key == "my-group"
    assert "translation_key" not in post.metadata.extra


def test_parse_no_translation_key_without_lang_suffix():
    settings = Settings(recursive=False, include_drafts=False)
    posts, errors, skipped = discover_and_parse_markdown(FIXTURES / "media-post", settings)
    assert not errors
    assert len(posts) == 1
    assert posts[0].metadata.translation_key == ""


def test_skips_drafts_by_default():
    settings = Settings(recursive=False, include_drafts=False)
    posts, errors, skipped = discover_and_parse_markdown(FIXTURES, settings)
    assert all("Draft Post" not in p.metadata.title for p in posts)
    assert any(reason == "draft" for _, reason in skipped)


def test_includes_drafts_when_requested():
    settings = Settings(recursive=False, include_drafts=True)
    posts, errors, skipped = discover_and_parse_markdown(FIXTURES, settings)
    assert any(p.metadata.title == "Draft Post" for p in posts)


def test_parses_featured_image():
    settings = Settings(recursive=False, include_drafts=False)
    posts, errors, skipped = discover_and_parse_markdown(FIXTURES / "media-post", settings)
    assert not errors
    assert len(posts) == 1
    post = posts[0]
    assert post.metadata.featured_image == "images/cover.png"
    assert "images/inline.png" in post.html_content
    assert "https://cdn.example.com/remote.png" in post.html_content
