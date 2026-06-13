from pathlib import Path

from md2wp.config import Settings
from md2wp.parsers.hugo_build import discover_and_parse_hugo_build, parse_hugo_index_html

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_hugo_index_html():
    settings = Settings()
    build_dir = FIXTURES
    post = parse_hugo_index_html(FIXTURES / "hugo-index.html", build_dir, settings)
    assert post.metadata.title == "Sample Hugo Post"
    assert post.metadata.lang == "en"
    assert "Go" in post.metadata.tags
    assert "TechBlog" in post.metadata.categories
    assert "Hugo rendered content" in post.html_content


def test_discover_hugo_build_flat(tmp_path):
    post_dir = tmp_path / "2024" / "06" / "12" / "sample-post"
    post_dir.mkdir(parents=True)
    (post_dir / "index.html").write_text((FIXTURES / "hugo-index.html").read_text())

    settings = Settings()
    posts, errors, skipped = discover_and_parse_hugo_build(tmp_path, settings)
    assert not errors
    assert len(posts) == 1
    assert posts[0].metadata.slug == "sample-post"
