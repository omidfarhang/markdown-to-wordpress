import os
import requests
from dotenv import load_dotenv
from utils.markdown_parser import parse_markdown_file, convert_markdown_to_html
from utils.wordpress import post_to_wordpress, export_to_wxr
from utils.hugo import crawl_hugo_build
from utils.export_utils import export_now  # Update import

# Load environment variables
load_dotenv()

WORDPRESS_URL = os.getenv("WORDPRESS_URL")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
MARKDOWN_DIRECTORY = os.getenv("MARKDOWN_DIRECTORY")
MARKDOWN_PARSER = os.getenv("MARKDOWN_PARSER", "normal")
EXPORT_DIRECTORY = os.getenv("EXPORT_DIRECTORY")

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
