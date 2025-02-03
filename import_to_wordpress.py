import os
import markdown
import requests
import yaml
import subprocess
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from datetime import datetime

# Load environment variables
load_dotenv()

WORDPRESS_URL = os.getenv("WORDPRESS_URL")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
MARKDOWN_DIRECTORY = os.getenv("MARKDOWN_DIRECTORY")
MARKDOWN_PARSER = os.getenv("MARKDOWN_PARSER", "normal")
EXPORT_DIRECTORY = os.getenv("EXPORT_DIRECTORY")
DOMAIN = os.getenv("DOMAIN")

def parse_markdown_file(file_path):
    """Parse metadata and content from the Markdown file."""
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    
    # Split YAML front matter from the content
    front_matter, markdown_content = content.split('---', 2)[1:]
    metadata = yaml.safe_load(front_matter)
    return metadata, markdown_content.strip()

def create_slug_from_url(url):
    """Extract slug from the URL by removing year, month, and day."""
    parts = url.strip("/").split("/")
    return parts[-1] if parts else ""

def convert_markdown_to_html(file_path):
    """Convert Markdown file to HTML based on the specified parser."""
    if MARKDOWN_PARSER == "hugo":
        result = subprocess.run(
            ["hugo", "convert", "toHTML", file_path],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Hugo conversion failed: {result.stderr}")
        return result.stdout
    elif MARKDOWN_PARSER == "jekyll":
        result = subprocess.run(
            ["jekyll", "build", "--source", file_path, "--destination", "output"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Jekyll conversion failed: {result.stderr}")
        with open("output/index.html", "r", encoding="utf-8") as file:
            return file.read()
    else:
        with open(file_path, "r", encoding="utf-8") as file:
            return markdown.markdown(file.read())

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

def extract_tags(soup):
    """Extract tags from the BeautifulSoup object."""
    tags = []
    tag_list = soup.find("ul", class_="post-tags")
    if tag_list:
        for tag in tag_list.find_all("a"):
            tags.append(tag.text.strip())
    return tags

def extract_categories(soup):
    """Extract categories from the BeautifulSoup object."""
    categories = []
    breadcrumbs = soup.find("div", class_="breadcrumbs")
    if breadcrumbs:
        links = breadcrumbs.find_all("a")
        if len(links) > 2:
            categories.append(links[2].text.strip())
    return categories

def crawl_hugo_build(build_directory):
    """Crawl the Hugo build directory and extract post data."""
    posts = []
    for root, dirs, files in os.walk(build_directory):
        # Limit the first level directories to those named as years
        if root == build_directory:
            dirs[:] = [d for d in dirs if d.isdigit() and len(d) == 4]
        if "index.html" in files:
            file_path = os.path.join(root, "index.html")
            with open(file_path, "r", encoding="utf-8") as file:
                soup = BeautifulSoup(file, "html.parser")
                
                # Extract title
                title_element = soup.find("h1", class_="post-title entry-hint-parent")
                if not title_element:
                    print(f"Error: Title not found in {file_path}")
                    continue
                title = title_element.text.strip()
                
                # Extract date
                date_element = soup.find("div", class_="post-meta").find("span", title=True)
                if not date_element:
                    print(f"Error: Date not found in {file_path}")
                    continue
                date = date_element["title"]
                
                # Extract content
                content_div = soup.find("div", class_="post-content")
                if not content_div:
                    print(f"Error: Content not found in {file_path}")
                    continue
                html_content = str(content_div)
                
                # Extract slug from directory name
                slug = os.path.basename(root)
                
                # Extract tags and categories
                tags = extract_tags(soup)
                categories = extract_categories(soup)
                
                # Create metadata dictionary
                metadata = {
                    "title": title,
                    "date": date,
                    "slug": create_slug_from_url(f"{build_directory}/{slug}/"),
                    "url": f"{build_directory}/{slug}/",
                    "tags": tags,
                    "categories": categories,
                    "lang": "en",  # Default language
                }
                
                posts.append((metadata, html_content))
    
    export_now(posts)

def main():
    """Main function to process Markdown files or crawl Hugo build."""
    
    if MARKDOWN_PARSER == "hugo_build":
        build_directory = os.getenv("HUGO_BUILD_DIRECTORY")
        if not os.path.isdir(build_directory):
            print(f"Error: Directory '{build_directory}' does not exist.")
            return
        crawl_hugo_build(build_directory)
    else:
        posts = []
        if not os.path.isdir(MARKDOWN_DIRECTORY):
            print(f"Error: Directory '{MARKDOWN_DIRECTORY}' does not exist.")
            return
        
        for file_name in os.listdir(MARKDOWN_DIRECTORY):
            if file_name.endswith(".md"):
                file_path = os.path.join(MARKDOWN_DIRECTORY, file_name)
                print(f"Processing file: {file_path}")
                
                metadata, markdown_content = parse_markdown_file(file_path)
                html_content = convert_markdown_to_html(file_path)
                
                posts.append((metadata, html_content))
        
        export_now(posts)

def export_now(posts):
    export_mode = os.getenv("EXPORT_MODE", "import")  # Default to 'import' mode

    if export_mode == "export":
        if not os.path.isdir(EXPORT_DIRECTORY):
            os.makedirs(EXPORT_DIRECTORY)
        export_to_wxr(posts, EXPORT_DIRECTORY)
    else:
        for metadata, html_content in posts:
            post_to_wordpress(metadata, html_content)

if __name__ == "__main__":
    main()
