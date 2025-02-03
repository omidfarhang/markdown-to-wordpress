import os
import markdown
import requests
import yaml
import subprocess
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

WORDPRESS_URL = os.getenv("WORDPRESS_URL")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
MARKDOWN_DIRECTORY = os.getenv("MARKDOWN_DIRECTORY")
MARKDOWN_PARSER = os.getenv("MARKDOWN_PARSER", "normal")
EXPORT_DIRECTORY = os.getenv("EXPORT_DIRECTORY")

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
    
    response = requests.post(
        f"{WORDPRESS_URL}/posts",
        json=post_data,
        auth=auth
    )
    if response.status_code == 201:
        print(f"Post '{metadata['title']}' created successfully!")
    else:
        print(f"Failed to create post: {response.status_code} - {response.text}")

def export_to_wxr(metadata, html_content, export_directory):
    """Export the extracted data to WordPress eXtended RSS (WXR) format."""
    slug = create_slug_from_url(metadata['url'])
    export_path = os.path.join(export_directory, f"{slug}.xml")
    
    wxr_content = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:wfw="http://wellformedweb.org/CommentAPI/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:wp="http://wordpress.org/export/1.2/">
<channel>
    <title>{metadata['title']}</title>
    <link>{metadata['url']}</link>
    <pubDate>{metadata['date']}</pubDate>
    <wp:post_type>post</wp:post_type>
    <wp:status>publish</wp:status>
    <wp:post_name>{slug}</wp:post_name>
    <wp:post_date>{metadata['date']}</wp:post_date>
    <wp:post_date_gmt>{metadata['date']}</wp:post_date_gmt>
    <wp:postmeta>
        <wp:meta_key>_wp_page_template</wp:meta_key>
        <wp:meta_value>default</wp:meta_value>
    </wp:postmeta>
    <content:encoded><![CDATA[{html_content}]]></content:encoded>
</channel>
</rss>"""
    
    with open(export_path, "w", encoding="utf-8") as file:
        file.write(wxr_content)
    
    print(f"Exported '{metadata['title']}' to {export_path}")

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
    for root, dirs, files in os.walk(build_directory):
        if "index.html" in files:
            file_path = os.path.join(root, "index.html")
            with open(file_path, "r", encoding="utf-8") as file:
                soup = BeautifulSoup(file, "html.parser")
                
                # Extract title
                title = soup.find("h1", class_="post-title entry-hint-parent").text.strip()
                
                # Extract date
                date = soup.find("div", class_="post-meta").find("span", title=True)["title"]
                
                # Extract content
                content_div = soup.find("div", class_="post-content")
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
                
                post_to_wordpress(metadata, html_content)

def main():
    """Main function to process Markdown files or crawl Hugo build."""
    export_mode = os.getenv("EXPORT_MODE", "import")  # Default to 'import' mode
    
    if MARKDOWN_PARSER == "hugo_build":
        build_directory = os.getenv("HUGO_BUILD_DIRECTORY")
        if not os.path.isdir(build_directory):
            print(f"Error: Directory '{build_directory}' does not exist.")
            return
        crawl_hugo_build(build_directory)
    else:
        if not os.path.isdir(MARKDOWN_DIRECTORY):
            print(f"Error: Directory '{MARKDOWN_DIRECTORY}' does not exist.")
            return
        
        for file_name in os.listdir(MARKDOWN_DIRECTORY):
            if file_name.endswith(".md"):
                file_path = os.path.join(MARKDOWN_DIRECTORY, file_name)
                print(f"Processing file: {file_path}")
                
                metadata, markdown_content = parse_markdown_file(file_path)
                html_content = convert_markdown_to_html(file_path)
                
                if export_mode == "export":
                    if not os.path.isdir(EXPORT_DIRECTORY):
                        os.makedirs(EXPORT_DIRECTORY)
                    export_to_wxr(metadata, html_content, EXPORT_DIRECTORY)
                else:
                    post_to_wordpress(metadata, html_content)

if __name__ == "__main__":
    main()
