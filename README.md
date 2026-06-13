# md2wp

Import Markdown or Hugo build output into WordPress via the REST API or WXR export.

## Features

- Parse Markdown files with YAML front matter (recursive scan)
- Crawl Hugo build output with configurable CSS selectors
- Publish to WordPress with tag/category resolution and slug upsert
- Export to WordPress WXR for offline migration
- Dry-run and validate commands for safe previews
- Configuration via CLI flags, `md2wp.toml`, or environment variables

## Quick start

```bash
git clone <repo-url>
cd markdown-to-wordpress
pip install -e ".[dev]"
```

Validate your content without touching WordPress:

```bash
md2wp validate --source ./content/posts
```

Preview what would be imported:

```bash
md2wp import --source ./content/posts --dry-run
```

## WordPress setup

1. Ensure the WordPress REST API is enabled (default on modern WordPress).
2. Create an [Application Password](https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/) for your user.
3. Set credentials:

```bash
export MD2WP_WORDPRESS_URL=https://yoursite.com/wp-json/wp/v2
export MD2WP_WORDPRESS_USERNAME=admin
export MD2WP_WORDPRESS_PASSWORD=xxxx xxxx xxxx xxxx
```

Import as drafts first (recommended):

```bash
md2wp import --source ./content/posts --status draft
```

## Usage

### Import Markdown

```bash
md2wp import --source ./content/posts --mode markdown --status draft
```

### Import from Hugo build

Build your Hugo site first, then import the rendered HTML:

```bash
hugo build
md2wp import --source ./public --mode hugo-build --status draft
```

### Export to WXR

```bash
md2wp export \
  --source ./content/posts \
  --output ./export/posts.xml \
  --domain https://yoursite.com
```

Import the resulting XML via **WordPress Admin → Tools → Import → WordPress**.

### Validate

```bash
md2wp validate --source ./content/posts
```

### Show configuration

```bash
md2wp config show
```

## Configuration

Precedence: **CLI flags > md2wp.toml > environment variables**.

Copy the example config:

```bash
cp md2wp.toml.example md2wp.toml
cp .env.example .env
```

See [`md2wp.toml.example`](md2wp.toml.example) for Hugo selector customization.

### Environment variables

| Variable | Description |
|----------|-------------|
| `MD2WP_WORDPRESS_URL` | WordPress REST API base URL |
| `MD2WP_WORDPRESS_USERNAME` | WordPress username |
| `MD2WP_WORDPRESS_PASSWORD` | Application password |
| `MD2WP_SOURCE` | Input directory |
| `MD2WP_MODE` | `markdown` or `hugo-build` |
| `MD2WP_STATUS` | `draft`, `publish`, or `private` |
| `DOMAIN` | Site URL for WXR export links |

Legacy variables (`WORDPRESS_URL`, `MARKDOWN_DIRECTORY`, `MARKDOWN_PARSER`, etc.) are still supported.

## Markdown format

```yaml
---
title: "My Post Title"
date: 2024-08-13T16:42:19+03:30
url: 2024/08/13/my-post/
tags:
  - Tag One
categories:
  - Blog
lang: en
draft: false
---
Your Markdown content here.
```

Required fields: `title`, `date`. Slug is derived from `url` or the filename.

Files named `_index.md` and posts with `draft: true` are skipped unless `--include-drafts` is set.

## Migration from the old script

| Old | New |
|-----|-----|
| `python import_to_wordpress.py` | `md2wp import` |
| `MARKDOWN_PARSER=normal` | `--mode markdown` |
| `MARKDOWN_PARSER=hugo_build` | `--mode hugo-build` |
| `EXPORT_MODE=export` | `md2wp export` |
| `MARKDOWN_DIRECTORY` | `--source` |

The old entry point still works but prints a deprecation warning.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```

## Troubleshooting

**Authentication failed** — Use an Application Password, not your login password. Ensure the REST API URL ends with `/wp-json/wp/v2`.

**Tags or categories missing** — md2wp resolves names to WordPress term IDs automatically. Check that your user can create terms.

**Duplicate posts on re-run** — md2wp upserts by slug. Ensure your Markdown `url` or filename produces a stable slug.

**Hugo build mode finds no posts** — Check CSS selectors in `md2wp.toml` match your theme. Run `md2wp validate --mode hugo-build` to see parse errors per file.

## License

MIT — see [LICENSE](LICENSE).
