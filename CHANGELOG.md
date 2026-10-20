# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.2] - 2026-10-20

### Removed

- Deprecated root shim `import_to_wordpress.py`; use `md2wp import` instead

### Changed

- Include `.env.example` and `tests/` in the source distribution

## [0.3.1] - 2026-10-20

### Fixed

- Build Intel macOS binaries on `macos-15-intel` (retired `macos-13` label never gets a runner)
- Bump release workflow actions to Node 24 runtimes (`upload-artifact@v7`, `download-artifact@v8`, `action-gh-release@v3`)

## [0.3.0] - 2026-10-20

### Added

- Interactive prompts for missing settings when running on a TTY (`prompt_missing_settings`, `--no-interactive` to disable)
- WordPress i18n settings (`wordpress.i18n.provider`, `link_translations`) via TOML, env, and examples
- `translation_key` on posts from frontmatter or `*.xx.md` filename stems
- Lang-scoped slug lookup and create/update query params for Polylang Pro / WPML; always write `lang` postmeta
- Optional second-pass translation linking (Polylang; WPML best-effort)
- Standalone binary builds via PyInstaller (`md2wp.spec`, optional `[bin]` extra)
- GitHub Actions release workflow that publishes Linux, macOS (Intel + ARM), and Windows binaries on `v*` tags
- README Quick start for downloading release binaries without installing Python

### Changed

- Prefer venv/`pip install .` for source installs; document binary downloads as the primary Quick start path

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
