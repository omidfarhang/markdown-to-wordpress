from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from md2wp.config import PostStatus, Settings
from md2wp.models import Post, PostMetadata
from md2wp.sinks.wxr import _wxr_datetimes, export_to_wxr

FIXTURES = Path(__file__).parent / "fixtures" / "media-post"
GOLDEN = Path(__file__).parent / "fixtures" / "wxr-golden.xml"
WP = "{http://wordpress.org/export/1.2/}"
TEHRAN = timezone(timedelta(hours=3, minutes=30))


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


def _export_xml(tmp_path: Path, post: Post) -> str:
    output = tmp_path / "export.xml"
    settings = Settings(
        output=output,
        domain="https://example.com",
        status=PostStatus.PUBLISH,
    )
    export_to_wxr([post], settings)
    return output.read_text(encoding="utf-8")


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
    xml = _export_xml(tmp_path, _media_post())

    assert "<wp:post_type>attachment</wp:post_type>" in xml
    assert "<wp:attachment_url>" in xml
    assert "https://example.com/wp-content/uploads/md2wp/inline.png" in xml
    assert "https://example.com/wp-content/uploads/md2wp/cover.png" in xml
    assert "images/inline.png" not in xml
    assert "https://cdn.example.com/remote.png" in xml
    assert "<wp:meta_key><![CDATA[_thumbnail_id]]></wp:meta_key>" in xml


def test_wxr_datetimes_naive_treated_as_utc():
    local, gmt, pub = _wxr_datetimes(datetime(2024, 8, 13, 16, 42, 19))
    assert local == "2024-08-13 16:42:19"
    assert gmt == "2024-08-13 16:42:19"
    assert pub == "Tue, 13 Aug 2024 16:42:19 GMT"


def test_wxr_datetimes_utc_aware():
    local, gmt, pub = _wxr_datetimes(
        datetime(2024, 8, 13, 16, 42, 19, tzinfo=timezone.utc)
    )
    assert local == "2024-08-13 16:42:19"
    assert gmt == "2024-08-13 16:42:19"
    assert pub == "Tue, 13 Aug 2024 16:42:19 GMT"


def test_wxr_datetimes_offset_plus_0330():
    local, gmt, pub = _wxr_datetimes(
        datetime(2024, 8, 13, 16, 42, 19, tzinfo=TEHRAN)
    )
    assert local == "2024-08-13 16:42:19"
    assert gmt == "2024-08-13 13:12:19"
    assert pub == "Tue, 13 Aug 2024 13:12:19 GMT"


def test_export_wxr_timezone_aware_distinct_local_and_gmt(tmp_path):
    post = Post(
        metadata=PostMetadata(
            title="Offset Post",
            date=datetime(2024, 8, 13, 16, 42, 19, tzinfo=TEHRAN),
            slug="offset-post",
        ),
        html_content="<p>Body</p>",
    )
    xml = _export_xml(tmp_path, post)

    assert "<wp:post_date><![CDATA[2024-08-13 16:42:19]]></wp:post_date>" in xml
    assert "<wp:post_date_gmt><![CDATA[2024-08-13 13:12:19]]></wp:post_date_gmt>" in xml
    assert "<wp:post_modified><![CDATA[2024-08-13 16:42:19]]></wp:post_modified>" in xml
    assert (
        "<wp:post_modified_gmt><![CDATA[2024-08-13 13:12:19]]></wp:post_modified_gmt>"
        in xml
    )
    assert "<pubDate>Tue, 13 Aug 2024 13:12:19 GMT</pubDate>" in xml


def test_export_wxr_naive_local_equals_gmt(tmp_path):
    xml = _export_xml(tmp_path, _sample_post())

    assert "<wp:post_date><![CDATA[2024-08-13 16:42:19]]></wp:post_date>" in xml
    assert "<wp:post_date_gmt><![CDATA[2024-08-13 16:42:19]]></wp:post_date_gmt>" in xml
    assert "<pubDate>Tue, 13 Aug 2024 16:42:19 GMT</pubDate>" in xml


def test_export_wxr_golden_fixture(tmp_path):
    output = tmp_path / "export.xml"
    settings = Settings(
        output=output,
        domain="https://example.com",
        status=PostStatus.PUBLISH,
        site_title="Golden Site",
        site_description="Golden fixture",
        site_language="en-US",
        wordpress_username="md2wp",
    )
    post = Post(
        metadata=PostMetadata(
            title="Golden Post",
            date=datetime(2024, 8, 13, 16, 42, 19, tzinfo=timezone.utc),
            slug="golden-post",
            tags=["Go"],
            categories=["Tech"],
            excerpt="Golden excerpt",
        ),
        html_content="<p>Golden body</p>",
    )
    export_to_wxr([post], settings)

    actual = output.read_text(encoding="utf-8")
    expected = GOLDEN.read_text(encoding="utf-8")
    assert actual == expected

    root = ET.parse(output).getroot()
    assert root.tag == "rss"
    item = root.find("channel/item")
    assert item is not None
    assert item.find(f"{WP}post_id").text == "459495"
    assert item.find(f"{WP}post_name").text == "golden-post"
    assert item.find("pubDate").text == "Tue, 13 Aug 2024 16:42:19 GMT"
