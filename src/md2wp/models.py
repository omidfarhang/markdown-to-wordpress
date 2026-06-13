from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class PostMetadata:
    title: str
    date: datetime
    slug: str
    url: str = ""
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    lang: str = "en"
    excerpt: str = ""
    shortlink: str = ""
    draft: bool = False
    source_path: Path | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Post:
    metadata: PostMetadata
    html_content: str


@dataclass
class ParseError:
    path: Path
    message: str


@dataclass
class ImportResult:
    posts: list[Post] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)
    published: int = 0
    updated: int = 0
    failed: int = 0
    dry_run: bool = False
    export_path: Path | None = None

    @property
    def success(self) -> bool:
        return self.failed == 0 and not self.errors
