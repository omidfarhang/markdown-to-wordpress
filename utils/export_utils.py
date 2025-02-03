import os
from utils.wordpress import post_to_wordpress, export_to_wxr

def export_now(posts):
    export_mode = os.getenv("EXPORT_MODE", "import")  # Default to 'import' mode

    if export_mode == "export":
        export_directory = os.getenv("EXPORT_DIRECTORY")
        if not os.path.isdir(export_directory):
            os.makedirs(export_directory)
        export_to_wxr(posts, export_directory)
    else:
        for metadata, html_content in posts:
            post_to_wordpress(metadata, html_content)
