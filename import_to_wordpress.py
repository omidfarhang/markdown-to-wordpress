import os
import markdown
import requests
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

WORDPRESS_URL = os.getenv("WORDPRESS_URL")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
MARKDOWN_DIRECTORY = os.getenv("MARKDOWN_DIRECTORY")

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

def main():
    """Main function to process Markdown files."""
    if not os.path.isdir(MARKDOWN_DIRECTORY):
        print(f"Error: Directory '{MARKDOWN_DIRECTORY}' does not exist.")
        return
    
    for file_name in os.listdir(MARKDOWN_DIRECTORY):
        if file_name.endswith(".md"):
            file_path = os.path.join(MARKDOWN_DIRECTORY, file_name)
            print(f"Processing file: {file_path}")
            
            metadata, markdown_content = parse_markdown_file(file_path)
            html_content = markdown.markdown(markdown_content)
            post_to_wordpress(metadata, html_content)

if __name__ == "__main__":
    main()
