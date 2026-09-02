from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest
from open_brain_engine.core.models import ValidationError
from open_brain_engine.core.ports import RedactedMarkdownDocument, RedactionReceipt
from open_brain_engine.storage.frontmatter import (
    AtomicMarkdownReader,
    AtomicMarkdownSink,
    FrontmatterError,
    markdown_relative_path,
    render_frontmatter,
)

from tests.unit.storage._factories import privacy, raw_capture


def _parse_rendered(value: str) -> tuple[dict[str, object], str]:
    frontmatter_text, body = value.removeprefix("---\n").split("\n---\n\n", 1)
    fields = {
        key: json.loads(encoded)
        for key, encoded in (line.split(": ", 1) for line in frontmatter_text.splitlines())
    }
    return fields, body


def _document(*, logical_key: str = "capture.synthetic-001") -> RedactedMarkdownDocument:
    fields = {
        "nested": {"list": [1, True, None, "value: # marker"]},
        "multiline": "line one\n---\nline two",
    }
    body = "Synthetic redacted body"
    output_digest = RedactedMarkdownDocument.output_digest_sha256(fields, body)
    return RedactedMarkdownDocument.create(
        document_id="note.synthetic-001",
        logical_key=logical_key,
        privacy_decision=privacy(),
        frontmatter=fields,
        body=body,
        redaction_receipt=RedactionReceipt.create(
            source_digest_sha256=sha256(b"synthetic source").hexdigest(),
            output_digest_sha256=output_digest,
            policy_version="redaction-v1",
        ),
    )


def test_frontmatter_round_trip_preserves_recursive_json_values() -> None:
    document = _document()
    document_fields = {key: value for key, value in document.to_dict().items() if key != "body"}
    rendered = render_frontmatter(fields=document_fields, body=document.body)
    fields, body = _parse_rendered(rendered)

    assert fields == document_fields
    assert body == document.body


@pytest.mark.parametrize(
    "fields",
    [
        {"Bad-Key": "value"},
        {"safe": 1.5},
        {"safe": object()},
        {"safe": "nul" + "\x00" + "value"},
        {"safe": {1: "non-string key"}},
    ],
)
def test_frontmatter_rejects_unsafe_keys_and_values(fields: dict[object, object]) -> None:
    with pytest.raises(FrontmatterError):
        render_frontmatter(fields=fields, body="synthetic")  # type: ignore[arg-type]


def test_frontmatter_rejects_non_whitespace_control_characters() -> None:
    with pytest.raises(FrontmatterError):
        render_frontmatter(fields={"safe": {"nested": "unsafe" + chr(1)}}, body="synthetic")


def test_capture_envelope_and_yaml_like_strings_render_as_json_data() -> None:
    envelope_fields = raw_capture().envelope.to_dict()
    fields = {
        **envelope_fields,
        "duplicate_structure": "same: first" + "\n" + "same: second",
        "yaml_delimiter": "-" * 3,
        "yaml_tag": "!!" + "python/object:synthetic",
    }

    rendered = render_frontmatter(fields=fields, body="Synthetic body")
    expected_lines = [
        "---",
        *(
            f"{key}: "
            + json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
            for key, value in sorted(fields.items())
        ),
        "---",
        "",
        "Synthetic body",
    ]

    assert rendered == "\n".join(expected_lines)
    assert set(envelope_fields) <= set(fields)
    assert 'yaml_tag: "!!python/object:synthetic"' in rendered
    assert 'yaml_delimiter: "---"' in rendered
    assert "same: first\\nsame: second" in rendered
    assert "\nsame: first\n" not in rendered


def test_percent_encoded_traversal_logical_key_is_rejected_before_io(
    tmp_path: Path,
) -> None:
    logical_key = "capture." + "%" + "2e" + "%" + "2e" + "%" + "2f" + "synthetic"

    with pytest.raises(ValidationError, match="invalid logical key"):
        _document(logical_key=logical_key)

    assert not tuple(tmp_path.iterdir())


def test_markdown_sink_uses_document_id_digest_not_logical_key_as_path(
    tmp_path: Path,
) -> None:
    document = _document()
    sink = AtomicMarkdownSink(root=tmp_path)
    reader = AtomicMarkdownReader(root=tmp_path)

    assert not hasattr(sink, "read_back")
    assert id(sink) != id(reader)

    result = sink.write_if_absent(document)
    path = tmp_path / markdown_relative_path(document.document_id)
    fields, body = _parse_rendered(path.read_text())

    assert result.record_id == document.document_id
    assert fields["redaction_receipt"] == document.redaction_receipt.to_dict()
    assert fields["privacy_decision"] == document.privacy_decision.to_dict()
    assert body == document.body
    assert document.logical_key not in str(path)
    assert reader.read_back(document.document_id) == path.read_bytes()
    assert result.digest_sha256 == sha256(path.read_bytes()).hexdigest()


def test_markdown_reader_returns_none_for_missing_document(tmp_path: Path) -> None:
    reader = AtomicMarkdownReader(root=tmp_path)

    assert reader.read_back("missing.synthetic-001") is None
