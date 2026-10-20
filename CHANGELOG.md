# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-20

### Added

- Local image discovery, WordPress REST media upload/reuse, content URL rewrite, and `featured_media` from frontmatter `featured_image` / `image`
- WXR attachment items (`wp:attachment_url`), content rewrite under `--domain`, and `_thumbnail_id` postmeta when a featured image is set
- `Settings.markdown_extensions` from `[markdown].extensions` in TOML
- Config and pipeline unit tests; WordPress media and WXR timezone/golden fixtures

### Fixed

- Load export path from `MD2WP_EXPORT_OUTPUT` (with legacy `EXPORT_DIRECTORY` fallback)
- WXR `post_date` / `post_modified` vs `*_gmt`: naive datetimes treated as UTC; aware datetimes keep wall time locally and convert GMT; `pubDate` as RFC 822

### Changed

- Document Application Password media-upload capability and WXR file-reachability notes in the README
- Prefer `pip install -e ".[dev]"`; remove root `requirements.txt`

## [0.1.0] - 2025-06-15

### Added

- Initial `md2wp` CLI: Markdown and Hugo-build import, WordPress REST upsert, WXR export, dry-run and validate
