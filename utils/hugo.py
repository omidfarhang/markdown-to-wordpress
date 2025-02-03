import os
from bs4 import BeautifulSoup
from utils.wordpress import create_slug_from_url, format_date, export_to_wxr
from utils.export_utils import export_now

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
            dirs[:] = [d for d in dirs if (d.isdigit() and len(d) == 4) or d == 'fa']
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
