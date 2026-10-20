# md2wp

Import Markdown or Hugo build output into WordPress via the REST API or WXR export.

## Features

- Parse Markdown files with YAML front matter (recursive scan)
- Crawl Hugo build output with configurable CSS selectors
- Publish to WordPress with tag/category resolution and slug upsert
- Optional Polylang Pro / WPML language assignment via REST (plus always-written `lang` postmeta)
- Upload local images and set featured media via the REST API
- Export to WordPress WXR for offline migration (including attachments)
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
   The user must be able to **upload media** (`upload_files`) as well as create posts.
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

Local images are rewritten to absolute URLs under `--domain`
(`{domain}/wp-content/uploads/md2wp/<filename>`) and emitted as WXR `attachment`
items. WordPress import still needs those files reachable at those URLs (or a
follow-up media sync)—copy files into the matching uploads path before or after
import if needed.

Post dates: timezone-aware values keep their wall-clock time in
`wp:post_date` / `wp:post_modified` and convert to UTC for `*_gmt` and RFC 822
`pubDate`. Naive datetimes are treated as UTC.

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

See [`md2wp.toml.example`](md2wp.toml.example) for Hugo selector customization and
`[wordpress.i18n]` defaults.

### Multilingual (Polylang / WPML)

REST import can assign languages through Polylang Pro or WPML when you set
`[wordpress.i18n]` in `md2wp.toml` (or the env vars below). Defaults keep today’s
behavior: `provider = "none"` writes plain postmeta only.

```toml
[wordpress.i18n]
# none | polylang | wpml
provider = "none"
# Link language variants after publish (requires provider != none)
link_translations = false
```

| Setting | Effect |
|---------|--------|
| `provider = "none"` | No language query params. Still writes postmeta `lang` when frontmatter has `lang`. |
| `provider = "polylang"` | Passes `?lang=<code>` on post GET/POST/PUT. Requires [Polylang Pro REST API](https://polylang.pro/documentation/support/developers/rest-api/); Free does not expose this. md2wp probes `/pll/v1/languages` and warns if missing. |
| `provider = "wpml"` | Passes `?wpml_language=<code>` on the same calls. Soft-warns if create/update responses never reflect the requested language. |
| `link_translations = true` | After all posts publish, groups variants by `translation_key` and links them. For Polylang, sends `translations[...]` query params. For WPML, logs a skip/warning (no stable public REST link endpoint). Ignored when `provider` is `none` (one warning). |

**Always:** after a successful create/update, md2wp sets postmeta `lang` to the
detected language—regardless of provider. Polylang/WPML ignore that meta for
their own language tables; it remains useful as a plain fallback.

WXR export does not emit Polylang/WPML taxonomies or translation links.

### Environment variables

| Variable | Description |
|----------|-------------|
| `MD2WP_WORDPRESS_URL` | WordPress REST API base URL |
| `MD2WP_WORDPRESS_USERNAME` | WordPress username |
| `MD2WP_WORDPRESS_PASSWORD` | Application password |
| `MD2WP_I18N_PROVIDER` | `none`, `polylang`, or `wpml` (see Multilingual) |
| `MD2WP_I18N_LINK_TRANSLATIONS` | `true` / `false` — link translation groups after publish |
| `MD2WP_SOURCE` | Input directory |
| `MD2WP_MODE` | `markdown` or `hugo-build` |
| `MD2WP_STATUS` | `draft`, `publish`, or `private` |
| `MD2WP_EXPORT_OUTPUT` | WXR export file path |
| `DOMAIN` | Site URL for WXR export links |

Legacy variables (`WORDPRESS_URL`, `MARKDOWN_DIRECTORY`, `MARKDOWN_PARSER`, `EXPORT_DIRECTORY`, etc.) are still supported.

Markdown Python-Markdown extensions are configured in `md2wp.toml` under `[markdown].extensions` (defaults: `fenced_code`, `tables`, `nl2br`).

## Markdown format

```yaml
---
title: "My Post Title"
date: 2024-08-13T16:42:19+03:30
url: 2024/08/13/my-post/
featured_image: images/cover.png
tags:
  - Tag One
categories:
  - Blog
lang: en
translation_key: my-post
draft: false
---
Your Markdown content here.

![Alt text](images/diagram.png)
```

Required fields: `title`, `date`. Slug is derived from `url` or the filename.

`lang` is written to WordPress postmeta on every REST publish. With
`wordpress.i18n.provider` set to `polylang` or `wpml`, the same code is also
sent as a REST query param (`?lang=` or `?wpml_language=`).

`translation_key` (aliases: `translation_of`, `translations_key`) groups language
variants for optional linking when `link_translations = true`. If omitted,
md2wp derives a key from filenames like `post.en.md` / `post.fr.md` (shared
stem `post`). Plain `post.md` without a lang suffix gets no automatic key.

`featured_image` (or `image`) sets the WordPress featured media. Relative paths
are resolved against the Markdown file’s directory. Relative `<img src>` values
in the body are uploaded (import) or rewritten to domain URLs (WXR export);
`http(s):` and `data:` sources are left unchanged.

Files named `_index.md` and posts with `draft: true` are skipped unless `--include-drafts` is set.

## Media

On **import**, md2wp:

1. Finds local `img[src]` paths in the HTML
2. Uploads each file via `POST /media` (or reuses an existing media item when
   the filename/slug already matches)
3. Rewrites `src` to the WordPress `source_url`
4. Sets `featured_media` when `featured_image` / `image` is present

Missing local files log a warning and leave the original `src` unchanged.

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

**Polylang language not applied** — `?lang=` requires Polylang Pro REST. Free Polylang will not honor language query params; md2wp still writes postmeta `lang`. Check the import-start probe warning for `/pll/v1/languages`.

**WPML language not applied** — Ensure `wordpress.i18n.provider = "wpml"` and that the site accepts `?wpml_language=` on posts. Translation *linking* via REST is not supported; link variants in WPML admin if needed.

## License

MIT — see [LICENSE](LICENSE).
