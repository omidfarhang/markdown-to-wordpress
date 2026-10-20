from datetime import datetime
from pathlib import Path

from md2wp.config import PostStatus, Settings
from md2wp.models import Post, PostMetadata
from md2wp.sinks.wxr import export_to_wxr

FIXTURES = Path(__file__).parent / "fixtures" / "media-post"


def _sample_post() -> Post:
    return Post(
        metadata=PostMetadata(
            title='Post with "quotes" & ampersands',
            date=datetime(2024, 8, 13, 16, 42, 19),
            slug="sample-post",
            tags=["Go"],
            categories=["TechBlog"],
            excerpt="Short excerpt",
        ),
        html_content="<p>Body & content</p>",
    )


def _media_post() -> Post:
    return Post(
        metadata=PostMetadata(
            title="Post With Images",
            date=datetime(2024, 8, 13, 16, 42, 19),
            slug="post-with-images",
            featured_image="images/cover.png",
            source_path=FIXTURES / "post.md",
        ),
        html_content=(
            '<p><img alt="Inline" src="images/inline.png"/>'
            '<img alt="Remote" src="https://cdn.example.com/remote.png"/></p>'
        ),
    )


def test_export_to_wxr(tmp_path):
    output = tmp_path / "export.xml"
    settings = Settings(
        output=output,
        domain="https://example.com",
        status=PostStatus.PUBLISH,
        site_title="Example Site",
    )
    result = export_to_wxr([_sample_post()], settings)
    xml = output.read_text(encoding="utf-8")

    assert result.export_path == output
    assert "<title>Example Site</title>" in xml
    assert 'Post with "quotes" &amp; ampersands' in xml
    assert "<wp:post_name>sample-post</wp:post_name>" in xml
    assert 'domain="post_tag"' in xml
    assert 'domain="category"' in xml
    assert "<![CDATA[<p>Body & content</p>]]>" in xml


def test_export_wxr_attachments_and_thumbnail(tmp_path):
    output = tmp_path / "export.xml"
    settings = Settings(
        output=output,
        domain="https://example.com",
        status=PostStatus.PUBLISH,
    )
    export_to_wxr([_media_post()], settings)
    xml = output.read_text(encoding="utf-8")

    assert "<wp:post_type>attachment</wp:post_type>" in xml
    assert "<wp:attachment_url>" in xml
    assert "https://example.com/wp-content/uploads/md2wp/inline.png" in xml
    assert "https://example.com/wp-content/uploads/md2wp/cover.png" in xml
    assert "images/inline.png" not in xml
    assert "https://cdn.example.com/remote.png" in xml
    assert "<wp:meta_key><![CDATA[_thumbnail_id]]></wp:meta_key>" in xml
