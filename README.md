# Markdown to WordPress Importer

This project provides a Python script to import Markdown blog posts into a WordPress site using the WordPress REST API. The script reads metadata and content from Markdown files, converts the content to HTML, and creates corresponding posts on WordPress.

## Features

- Extracts metadata such as title, date, tags, categories, and language from Markdown files.
- Converts Markdown content to HTML.
- Supports slug customization by extracting the last segment of the URL.
- Automatically posts content to WordPress with proper authentication.
- Supports different Markdown parsers: normal, Hugo, and Jekyll.
- Extracts tags and categories from Hugo build HTML files.
- Imports from Jekyll and Hugo single files.
- Crawls Hugo build directories to extract and import posts.

---

## Prerequisites

1. Python 3.x installed on your system.
2. WordPress REST API enabled on your WordPress site.
3. A WordPress account with sufficient permissions to create posts.
4. Required Python libraries installed:

   ```bash
   pip install markdown PyYAML requests python-dotenv beautifulsoup4
   ```

---

## Installation

1. Clone or download this repository.
2. Navigate to the project directory:

   ```bash
   cd markdown-to-wordpress
   ```

---

## Configuration

1. Copy `.env.example` to `.env` and fill in your credentials:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` to include your WordPress details:

   ```plaintext
   WORDPRESS_URL=https://yourwordpresssite.com/wp-json/wp/v2
   USERNAME=your_username
   PASSWORD=your_password
   MARKDOWN_DIRECTORY=/path/to/markdown/files
   MARKDOWN_PARSER=normal  # Options: normal, hugo, jekyll, hugo_build
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

1. Ensure all your Markdown files are in the specified directory. Each file should follow the format:
   - YAML front matter for metadata (e.g., title, date, tags, categories, etc.).
   - Markdown content below the front matter.

2. Run the script:

   ```bash
   python import_to_wordpress.py
   ```

3. The script will:
   - Read each `.md` file in the directory.
   - Parse the YAML front matter and Markdown content.
   - Convert the content to HTML using the specified parser.
   - Create a new WordPress post using the WordPress REST API.
   - If using Hugo build, it will crawl the build directory to extract and import posts.

---

## Example Markdown File

```yaml
---
title: "The Hidden World of Esoteric Programming Languages"
date: 2024-08-13T16:42:19+03:30
url: 2024/08/13/the-hidden-world-of-esoteric-programming-languages/
shortlink: https://g.omid.dev/hQlrMEU
tags:
  - Esoteric Programming Languages
  - Brainfuck
  - Whitespace
lang: en
categories: 
  - TechBlog
---
Your Markdown content goes here.
```

---

## Notes

- To test the script without publishing posts, change `"status": "publish"` to `"status": "draft"` in the `post_to_wordpress` function.
- Ensure your WordPress site allows remote API access.
- Use the "Application Passwords" plugin for secure authentication.

---

## Troubleshooting

1. **Authentication Error**: Ensure the username and password are correct and the API endpoint is accessible.
2. **Invalid API Response**: Check your WordPress logs for details or verify your metadata format in the Markdown files.
3. **Markdown Conversion Issues**: Ensure the Markdown follows proper syntax, as the script uses the `markdown` library for conversion.

---

## License

This project is licensed under the MIT License. Feel free to use and modify it as needed.
