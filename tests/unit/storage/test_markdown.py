from __future__ import annotations

from types import MappingProxyType

import pytest

from open_brain.storage.markdown import MarkdownFormatError, parse_markdown, render_markdown


def test_markdown_round_trip_is_deterministic_and_preserves_metadata() -> None:
    fields = {
        "captured_at": "2026-01-02T03:04:05Z",
        "custom": {"labels": ["synthetic", "public"], "reviewed": True},
        "page_id": "note.synthetic-001",
    }
    body = "# Synthetic note\n\nBody with [[Synthetic link]]."

    rendered = render_markdown(fields=fields, body=body)
    parsed = parse_markdown(rendered.encode("utf-8"))

    assert rendered == (
        "---\n"
        'captured_at: "2026-01-02T03:04:05Z"\n'
        'custom: {"labels":["synthetic","public"],"reviewed":true}\n'
        'page_id: "note.synthetic-001"\n'
        "---\n\n"
        "# Synthetic note\n\nBody with [[Synthetic link]]."
    )
    assert parsed.fields == fields
    assert isinstance(parsed.fields, MappingProxyType)
    assert parsed.body == body


@pytest.mark.parametrize(
    "payload",
    [
        "Synthetic body without frontmatter",
        "---\npage_id: not-json\n---\n\nBody",
        '---\npage_id: "first"\npage_id: "second"\n---\n\nBody',
        '---\nBad-Key: "value"\n---\n\nBody',
        '---\npage_id: "note.synthetic-001"\n---\nBody',
    ],
)
def test_markdown_parser_fails_closed_on_malformed_frontmatter(payload: str) -> None:
    with pytest.raises(MarkdownFormatError, match="invalid Markdown frontmatter"):
        parse_markdown(payload)
