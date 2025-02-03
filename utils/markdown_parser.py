import os
import markdown
import subprocess
import yaml

MARKDOWN_PARSER = os.getenv("MARKDOWN_PARSER", "normal")

def parse_markdown_file(file_path):
    """Parse metadata and content from the Markdown file."""
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    
    # Split YAML front matter from the content
    front_matter, markdown_content = content.split('---', 2)[1:]
    metadata = yaml.safe_load(front_matter)
    return metadata, markdown_content.strip()

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
