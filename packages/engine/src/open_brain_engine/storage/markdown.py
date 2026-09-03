"""Deterministic Markdown documents with JSON-compatible frontmatter."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .frontmatter import FrontmatterError, render_frontmatter

_KEY_PATTERN = re.compile(r"[a-z][a-z0-9_]*")
_OPENING = "---\n"
_SEPARATOR = "\n---\n\n"


class MarkdownFormatError(ValueError):
    """A Markdown document is outside the public deterministic format."""


@dataclass(frozen=True, slots=True)
class ParsedMarkdown:
    fields: Mapping[str, object]
    body: str


def render_markdown(*, fields: Mapping[str, object], body: str) -> str:
    """Render the public deterministic Markdown format."""

    try:
        return render_frontmatter(fields=fields, body=body)
    except (FrontmatterError, TypeError, ValueError):
        raise MarkdownFormatError("invalid Markdown frontmatter") from None


def parse_markdown(payload: str | bytes) -> ParsedMarkdown:
    """Parse deterministic JSON-line frontmatter without invoking a YAML loader."""

    try:
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    except UnicodeDecodeError:
        raise MarkdownFormatError("invalid Markdown frontmatter") from None
    if not isinstance(text, str) or not text.startswith(_OPENING) or _SEPARATOR not in text:
        raise MarkdownFormatError("invalid Markdown frontmatter")
    frontmatter_text, body = text.removeprefix(_OPENING).split(_SEPARATOR, 1)
    if not frontmatter_text:
        raise MarkdownFormatError("invalid Markdown frontmatter")

    fields: dict[str, object] = {}
    try:
        for line in frontmatter_text.splitlines():
            key, encoded = line.split(": ", 1)
            if not _KEY_PATTERN.fullmatch(key) or key in fields:
                raise ValueError
            fields[key] = json.loads(encoded, object_pairs_hook=_unique_object)
        render_frontmatter(fields=fields, body=body)
    except (FrontmatterError, TypeError, ValueError, json.JSONDecodeError):
        raise MarkdownFormatError("invalid Markdown frontmatter") from None
    return ParsedMarkdown(fields=MappingProxyType(fields), body=body)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value
