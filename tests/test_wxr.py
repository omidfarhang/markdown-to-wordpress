from datetime import datetime

from md2wp.config import PostStatus, Settings
from md2wp.models import Post, PostMetadata
from md2wp.sinks.wxr import export_to_wxr


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
    assert "Post with \"quotes\" &amp; ampersands" in xml
    assert "<wp:post_name>sample-post</wp:post_name>" in xml
    assert "domain=\"post_tag\"" in xml
    assert "domain=\"category\"" in xml
    assert "<![CDATA[<p>Body & content</p>]]>" in xml
