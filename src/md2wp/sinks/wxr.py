from __future__ import annotations

import hashlib
from datetime import timezone
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape

from md2wp.config import Settings
from md2wp.logging import get_logger
from md2wp.media import collect_local_images, resolve_featured_path, rewrite_image_srcs
from md2wp.models import ImportResult, Post

logger = get_logger(__name__)


def _format_wxr_datetime(value) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _stable_post_id(slug: str) -> int:
    digest = hashlib.sha256(slug.encode()).hexdigest()
    return int(digest[:8], 16) % 900000 + 100000


def _stable_attachment_id(path: Path) -> int:
    digest = hashlib.sha256(str(path.resolve()).encode()).hexdigest()
    return int(digest[:8], 16) % 900000 + 200000


def _attachment_url(domain: str, path: Path) -> str:
    """Absolute URL under export domain for WXR attachment_url / content rewrite."""
    filename = quote(path.name)
    return f"{domain}/wp-content/uploads/md2wp/{filename}"


def _postmeta(key: str, value: str) -> list[str]:
    return [
        "        <wp:postmeta>",
        f"            <wp:meta_key><![CDATA[{key}]]></wp:meta_key>",
        f"            <wp:meta_value><![CDATA[{value}]]></wp:meta_value>",
        "        </wp:postmeta>",
    ]


def _emit_attachment(
    lines: list[str],
    *,
    attachment_id: int,
    path: Path,
    url: str,
    creator: str,
    parent_id: int,
    date_str: str,
) -> None:
    title = path.stem
    lines.extend(
        [
            "    <item>",
            f"        <title>{escape(title)}</title>",
            f"        <link>{escape(url)}</link>",
            f"        <pubDate>{escape(date_str)}</pubDate>",
            f"        <dc:creator>{escape(creator)}</dc:creator>",
            f'        <guid isPermaLink="false">{escape(url)}</guid>',
            "        <description></description>",
            "        <content:encoded><![CDATA[]]></content:encoded>",
            "        <excerpt:encoded><![CDATA[]]></excerpt:encoded>",
            f"        <wp:post_id>{attachment_id}</wp:post_id>",
            f"        <wp:post_date><![CDATA[{date_str}]]></wp:post_date>",
            f"        <wp:post_date_gmt><![CDATA[{date_str}]]></wp:post_date_gmt>",
            f"        <wp:post_modified><![CDATA[{date_str}]]></wp:post_modified>",
            f"        <wp:post_modified_gmt><![CDATA[{date_str}]]></wp:post_modified_gmt>",
            "        <wp:comment_status>closed</wp:comment_status>",
            "        <wp:ping_status>closed</wp:ping_status>",
            f"        <wp:post_name>{escape(path.stem)}</wp:post_name>",
            "        <wp:status>inherit</wp:status>",
            f"        <wp:post_parent>{parent_id}</wp:post_parent>",
            "        <wp:menu_order>0</wp:menu_order>",
            "        <wp:post_type>attachment</wp:post_type>",
            "        <wp:post_password></wp:post_password>",
            "        <wp:is_sticky>0</wp:is_sticky>",
            f"        <wp:attachment_url><![CDATA[{url}]]></wp:attachment_url>",
            "    </item>",
        ]
    )


def _prepare_post_media(
    post: Post, domain: str
) -> tuple[str, list[tuple[Path, int, str]], int | None]:
    """
    Collect local images, build attachment descriptors, rewrite HTML.

    Returns (html, [(path, attachment_id, url), ...], featured_attachment_id).
    """
    base_dir = post.metadata.source_path.parent if post.metadata.source_path else Path(".")
    html = post.html_content
    src_map: dict[str, str] = {}
    attachments: list[tuple[Path, int, str]] = []
    path_to_id: dict[Path, int] = {}

    for original_src, abs_path in collect_local_images(html, base_dir):
        resolved = abs_path.resolve()
        if resolved in path_to_id:
            att_id = path_to_id[resolved]
            url = _attachment_url(domain, resolved)
        else:
            att_id = _stable_attachment_id(resolved)
            url = _attachment_url(domain, resolved)
            path_to_id[resolved] = att_id
            attachments.append((resolved, att_id, url))
        src_map[original_src] = url

    featured_id: int | None = None
    featured_path = resolve_featured_path(post.metadata.featured_image, base_dir)
    if featured_path:
        resolved = featured_path.resolve()
        if resolved in path_to_id:
            featured_id = path_to_id[resolved]
        else:
            att_id = _stable_attachment_id(resolved)
            url = _attachment_url(domain, resolved)
            path_to_id[resolved] = att_id
            attachments.append((resolved, att_id, url))
            featured_id = att_id

    html = rewrite_image_srcs(html, src_map)
    return html, attachments, featured_id


def export_to_wxr(posts: list[Post], settings: Settings) -> ImportResult:
    if not settings.output:
        raise ValueError("Output path is required for WXR export (--output)")
    if not settings.domain:
        raise ValueError("Domain is required for WXR export (--domain or site.domain in config)")

    domain = settings.domain.rstrip("/")
    creator = settings.wordpress_username or "md2wp"

    lines = [
        '<?xml version="1.0" encoding="UTF-8" ?>',
        '<rss version="2.0"',
        ' xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/"',
        ' xmlns:content="http://purl.org/rss/1.0/modules/content/"',
        ' xmlns:wfw="http://wellformedweb.org/CommentAPI/"',
        ' xmlns:dc="http://purl.org/dc/elements/1.1/"',
        ' xmlns:wp="http://wordpress.org/export/1.2/">',
        "<channel>",
        f"    <title>{escape(settings.site_title)}</title>",
        f"    <link>{escape(domain)}</link>",
        f"    <description>{escape(settings.site_description)}</description>",
        f"    <language>{escape(settings.site_language)}</language>",
        "    <wp:wxr_version>1.2</wp:wxr_version>",
    ]

    for post in posts:
        slug = post.metadata.slug
        post_id = _stable_post_id(slug)
        formatted_date = _format_wxr_datetime(post.metadata.date)
        link = f"{domain}/{slug}/"
        html_content, attachments, featured_id = _prepare_post_media(post, domain)

        lines.extend(
            [
                "    <item>",
                f"        <title>{escape(post.metadata.title)}</title>",
                f"        <link>{escape(link)}</link>",
                f"        <pubDate>{escape(formatted_date)}</pubDate>",
                f"        <dc:creator>{escape(creator)}</dc:creator>",
                f'        <guid isPermaLink="false">{escape(link)}</guid>',
                "        <description></description>",
                f"        <content:encoded><![CDATA[{html_content}]]></content:encoded>",
                f"        <excerpt:encoded><![CDATA[{post.metadata.excerpt}]]></excerpt:encoded>",
                f"        <wp:post_id>{post_id}</wp:post_id>",
                f"        <wp:post_date><![CDATA[{formatted_date}]]></wp:post_date>",
                f"        <wp:post_date_gmt><![CDATA[{formatted_date}]]></wp:post_date_gmt>",
                f"        <wp:post_modified><![CDATA[{formatted_date}]]></wp:post_modified>",
                f"        <wp:post_modified_gmt>"
                f"<![CDATA[{formatted_date}]]></wp:post_modified_gmt>",
                "        <wp:comment_status>closed</wp:comment_status>",
                "        <wp:ping_status>closed</wp:ping_status>",
                f"        <wp:post_name>{escape(slug)}</wp:post_name>",
                f"        <wp:status>{settings.status.value}</wp:status>",
                "        <wp:post_parent>0</wp:post_parent>",
                "        <wp:menu_order>0</wp:menu_order>",
                "        <wp:post_type>post</wp:post_type>",
                "        <wp:post_password></wp:post_password>",
                "        <wp:is_sticky>0</wp:is_sticky>",
            ]
        )

        for category in post.metadata.categories:
            nicename = category.lower().replace(" ", "-")
            lines.append(
                f'        <category domain="category" nicename="{escape(nicename)}">'
                f"<![CDATA[{category}]]></category>"
            )

        for tag in post.metadata.tags:
            nicename = tag.lower().replace(" ", "-")
            lines.append(
                f'        <category domain="post_tag" nicename="{escape(nicename)}">'
                f"<![CDATA[{tag}]]></category>"
            )

        if featured_id is not None:
            lines.extend(_postmeta("_thumbnail_id", str(featured_id)))

        lines.append("    </item>")

        for path, att_id, url in attachments:
            _emit_attachment(
                lines,
                attachment_id=att_id,
                path=path,
                url=url,
                creator=creator,
                parent_id=post_id,
                date_str=formatted_date,
            )

    lines.extend(["</channel>", "</rss>"])

    settings.output.parent.mkdir(parents=True, exist_ok=True)
    settings.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Exported %d posts to %s", len(posts), settings.output)

    return ImportResult(
        posts=posts,
        export_path=settings.output,
        dry_run=False,
    )
