# Contributing

Thanks for contributing to md2wp. This guide covers local setup, checks, and releases.

## Development setup

Requires Python 3.10+.

```bash
git clone https://github.com/omidfarhang/markdown-to-wordpress.git
cd markdown-to-wordpress
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

On Arch/Manjaro and other PEP 668 systems, always use a venv (or pipx) — do not `pip install` into system Python.

## Checks

Run before opening a PR:

```bash
ruff check src tests
pytest
```

CI runs the same checks on Python 3.10 and 3.12.

## Project layout

- `src/md2wp/` — package (CLI, config, parsers, WordPress/WXR sinks)
- `tests/` — pytest suite and fixtures
- `md2wp.toml.example` / `.env.example` — keep in sync when adding settings

## Standalone binaries

Optional local build:

```bash
pip install -e ".[bin]"
pyinstaller --noconfirm --clean md2wp.spec
./dist/md2wp --help
```

GitHub Actions (`.github/workflows/release.yml`) builds Linux, macOS, and Windows binaries. Pushing a `v*` tag creates a GitHub Release with those artifacts. `workflow_dispatch` builds artifacts without publishing a release (useful for smoke-testing the packaging).

## Versioning and changelog

This project follows [Semantic Versioning](https://semver.org/) and [Keep a Changelog](https://keepachangelog.com/).

When you change user-facing behavior:

1. Bump `version` in `pyproject.toml` and `__version__` in `src/md2wp/__init__.py`
2. Add an entry under `CHANGELOG.md`
3. Tag the release as `vX.Y.Z` and push the tag to publish binaries

## Pull requests

- Keep PRs focused; match existing code style and naming
- Prefer tests for bug fixes and new behavior
- Update the README when commands, config keys, or install steps change
- Do not commit secrets (`.env`, credentials, Application Passwords)

## License

By contributing, you agree that your contributions are licensed under the MIT License (see [LICENSE](LICENSE)).
