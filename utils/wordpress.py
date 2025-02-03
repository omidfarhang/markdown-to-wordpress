import os
import requests
from datetime import datetime

WORDPRESS_URL = os.getenv("WORDPRESS_URL")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
DOMAIN = os.getenv("DOMAIN")

def create_slug_from_url(url):
    """Extract slug from the URL by removing year, month, and day."""
    parts = url.strip("/").split("/")
    return parts[-1] if parts else ""

def post_to_wordpress(metadata, html_content):
    """Post the extracted data to WordPress."""
    auth = (USERNAME, PASSWORD)
    slug = create_slug_from_url(metadata['url'])
    
    post_data = {
        "title": metadata["title"],
        "date": metadata["date"],
        "slug": slug,
        "shortlink": metadata.get("shortlink"),
        "tags": metadata.get("tags", []),
        "categories": metadata.get("categories", []),
        "content": html_content,
        "status": "publish",  # Set to 'draft' for testing
        "lang": metadata.get("lang", "en"),
    }
    
    if not WORDPRESS_URL:
        print("Error: WORDPRESS_URL is not set.")
        return
    
    response = requests.post(
        f"{WORDPRESS_URL}/posts",
        json=post_data,
        auth=auth
    )
    if response.status_code == 201:
        print(f"Post '{metadata['title']}' created successfully!")
    else:
        print(f"Failed to create post: {response.status_code} - {response.text}")

def format_date(date_str):
    """Format date to 'Mon, 12 Jun 2023 20:40:00 +0000'."""
    try:
        date_obj = datetime.strptime(date_str, "%b %d, %Y %I:%M %p %Z")
    except ValueError:
        date_obj = datetime.strptime(date_str, "%b %d, %Y %I:%M %p %z")
    return date_obj.strftime("%a, %d %b %Y %H:%M:%S +0000")

def export_to_wxr(posts, export_directory):
    """Export the extracted data to a single WordPress eXtended RSS (WXR) format."""
    export_path = os.path.join(export_directory, "exported_posts.xml")
    
    wxr_content = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:wfw="http://wellformedweb.org/CommentAPI/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:wp="http://wordpress.org/export/1.2/">
<channel>"""
    
    for metadata, html_content in posts:
        slug = create_slug_from_url(metadata['url'])
        formatted_date = format_date(metadata['date'])
        wxr_content += f"""
    <item>
        <title>{metadata['title']}</title>
        <link>{DOMAIN}/{slug}/</link>
        <pubDate>{formatted_date}</pubDate>
        <wp:post_type>post</wp:post_type>
        <wp:status>publish</wp:status>
        <wp:post_name>{slug}</wp:post_name>
        <wp:post_date>{formatted_date}</wp:post_date>
        <wp:post_date_gmt>{formatted_date}</wp:post_date_gmt>
        <wp:postmeta>
            <wp:meta_key>_wp_page_template</wp:meta_key>
            <wp:meta_value>default</wp:meta_value>
        </wp:postmeta>
        <category><![CDATA[{', '.join(metadata.get('categories', []))}]]></category>
        <tag><![CDATA[{', '.join(metadata.get('tags', []))}]]></tag>
        <content:encoded><![CDATA[{html_content}]]></content:encoded>
    </item>"""
    
    wxr_content += """
</channel>
</rss>"""
    
    with open(export_path, "w", encoding="utf-8") as file:
        file.write(wxr_content)
    
    print(f"Exported all posts to {export_path}")
