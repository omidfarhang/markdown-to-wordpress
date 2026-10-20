from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup, Comment, Tag

LANGUAGE_CLASS_RE = re.compile(r"^(?:language|lang)-(.+)$", re.IGNORECASE)
LANGUAGE_SAFE_RE = re.compile(r"[^a-zA-Z0-9_+#-]+")
HIGHLIGHT_WRAPPER_CLASSES = frozenset(
    {"highlight", "highlighter-rouge", "codehilite", "chroma"}
)


def _class_list(tag: Tag) -> list[str]:
    classes = tag.get("class") or []
    if isinstance(classes, str):
        return classes.split()
    return [str(c) for c in classes]


def _sanitize_language(raw: str) -> str:
    cleaned = LANGUAGE_SAFE_RE.sub("", raw.strip())
    return cleaned.lower()


def _language_from_tag(tag: Tag) -> str | None:
    for attr in ("data-lang", "data-language"):
        value = tag.get(attr)
        if value:
            sanitized = _sanitize_language(str(value))
            if sanitized:
                return sanitized

    for cls in _class_list(tag):
        match = LANGUAGE_CLASS_RE.match(cls)
        if match:
            sanitized = _sanitize_language(match.group(1))
            if sanitized:
                return sanitized
    return None


def _is_already_gutenberg(pre: Tag) -> bool:
    if "wp-block-code" in _class_list(pre):
        return True

    prev = pre.previous_sibling
    while prev is not None and isinstance(prev, str) and not str(prev).strip():
        prev = prev.previous_sibling
    if isinstance(prev, Comment):
        text = str(prev).strip()
        if text.startswith("wp:code"):
            return True
    return False


def _highlight_wrapper(pre: Tag) -> Tag | None:
    parent = pre.parent
    if not isinstance(parent, Tag) or parent.name != "div":
        return None

    parent_classes = set(_class_list(parent))
    if not parent_classes.intersection(HIGHLIGHT_WRAPPER_CLASSES):
        return None

    significant = [
        child
        for child in parent.children
        if not (isinstance(child, str) and not str(child).strip())
        and not isinstance(child, Comment)
    ]
    if len(significant) == 1 and significant[0] is pre:
        return parent
    # Hugo often nests: div.highlight > div.chroma > pre, or div.highlight > pre.chroma
    if len(significant) == 1 and isinstance(significant[0], Tag):
        inner = significant[0]
        if inner.name == "div" and set(_class_list(inner)).intersection(
            HIGHLIGHT_WRAPPER_CLASSES
        ):
            inner_kids = [
                child
                for child in inner.children
                if not (isinstance(child, str) and not str(child).strip())
                and not isinstance(child, Comment)
            ]
            if len(inner_kids) == 1 and inner_kids[0] is pre:
                return parent
    return None


def _code_child(pre: Tag) -> Tag | None:
    for child in pre.children:
        if isinstance(child, Tag) and child.name == "code":
            return child
    code = pre.find("code")
    return code if isinstance(code, Tag) else None


def _build_block_fragment(soup: BeautifulSoup, code: Tag, language: str | None) -> list:
    new_pre = soup.new_tag("pre")
    new_pre["class"] = ["wp-block-code"]

    new_code = soup.new_tag("code")
    if language:
        new_code["class"] = [f"language-{language}"]

    for child in list(code.contents):
        new_code.append(child.extract())
    new_pre.append(new_code)

    if language:
        opener = Comment(f' wp:code {json.dumps({"language": language}, separators=(",", ":"))} ')
    else:
        opener = Comment(" wp:code ")
    closer = Comment(" /wp:code ")
    return [opener, new_pre, closer]


def wrap_code_blocks(html: str) -> str:
    """Wrap classic <pre><code> fences as Gutenberg wp:code blocks.

    Preserves highlighter-friendly language-* classes and adds a language
    attribute on the block comment when a language can be detected.
    Idempotent for content that is already wrapped.
    """
    if not html or not html.strip():
        return html

    soup = BeautifulSoup(html, "html.parser")
    targets: list[tuple[Tag, Tag]] = []

    for pre in soup.find_all("pre"):
        if not isinstance(pre, Tag):
            continue
        if _is_already_gutenberg(pre):
            continue
        code = _code_child(pre)
        if code is None:
            continue
        targets.append((pre, code))

    for pre, code in targets:
        if pre.parent is None:
            continue
        language = _language_from_tag(code) or _language_from_tag(pre)
        replace_node: Tag = _highlight_wrapper(pre) or pre
        nodes = _build_block_fragment(soup, code, language)
        replace_node.replace_with(*nodes)

    return str(soup)
