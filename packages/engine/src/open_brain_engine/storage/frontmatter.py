from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path, PurePosixPath

from open_brain_engine.core.models import PrivacyDecision, PrivacyReason, PrivacyTier
from open_brain_engine.core.ports import PutDisposition, PutResult, RedactedMarkdownDocument

from .filesystem import DurabilityError, StorageError, WriteState, atomic_write_new, read_confined


class FrontmatterError(ValueError):
    """Frontmatter contains a value outside the safe JSON-compatible subset."""


def _allows_work_tier_persistence(decision: PrivacyDecision) -> bool:
    return (
        (
            decision.tier is PrivacyTier.PUBLIC
            and decision.reason is PrivacyReason.POLICY_PUBLIC
            and decision.confirmation_ref is None
        )
        or (
            decision.tier is PrivacyTier.WORK
            and decision.reason is PrivacyReason.POLICY_WORK
            and decision.confirmation_ref is None
        )
        or (
            decision.tier is PrivacyTier.PERSONAL
            and decision.reason is PrivacyReason.PERSONAL_CONFIRMED
            and decision.confirmation_ref is not None
        )
    )


_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def _normalize_text(value: str, *, field: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    if any(
        unicodedata.category(character) == "Cc" and character not in {"\t", "\n", "\r"}
        for character in normalized
    ):
        raise FrontmatterError(f"unsafe frontmatter {field}")
    return normalized


def _normalize_value(value: object, *, top_level: bool = False) -> object:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        raise FrontmatterError("unsafe frontmatter value")
    if isinstance(value, str):
        return _normalize_text(value, field="value")
    if isinstance(value, tuple | list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, Mapping):
        normalized_mapping: dict[str, object] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str):
                raise FrontmatterError("unsafe frontmatter key")
            key = _normalize_text(raw_key, field="key")
            if top_level and not _KEY_PATTERN.fullmatch(key):
                raise FrontmatterError("unsafe frontmatter key")
            if key in normalized_mapping:
                raise FrontmatterError("duplicate frontmatter key")
            normalized_mapping[key] = _normalize_value(raw_value)
        return dict(sorted(normalized_mapping.items()))
    raise FrontmatterError("unsafe frontmatter value")


def render_frontmatter(*, fields: Mapping[str, object], body: str) -> str:
    if not isinstance(body, str):
        raise FrontmatterError("unsafe Markdown body")
    normalized = _normalize_value(fields, top_level=True)
    if not isinstance(normalized, dict):
        raise FrontmatterError("invalid frontmatter")
    lines = ["---"]
    for key, value in normalized.items():
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        lines.append(f"{key}: {encoded}")
    lines.extend(("---", "", _normalize_text(body, field="body")))
    return "\n".join(lines)


def markdown_relative_path(document_id: str) -> PurePosixPath:
    if not isinstance(document_id, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", document_id
    ):
        raise StorageError("invalid Markdown document identifier")
    digest = sha256(document_id.encode("utf-8")).hexdigest()
    return PurePosixPath("notes", digest[:2], digest + ".md")


class AtomicMarkdownSink:
    def __init__(self, *, root: Path) -> None:
        self._root = root

    def write_if_absent(self, document: RedactedMarkdownDocument) -> PutResult:
        if not isinstance(document, RedactedMarkdownDocument):
            raise StorageError("invalid redacted Markdown document")
        if not _allows_work_tier_persistence(document.privacy_decision):
            raise StorageError("work-tier privacy decision rejected")
        payload = rendered_markdown_bytes(document)
        state = atomic_write_new(
            root=self._root,
            relative=markdown_relative_path(document.document_id),
            data=payload,
        )
        return PutResult(
            disposition=(
                PutDisposition.CREATED if state is WriteState.CREATED else PutDisposition.DUPLICATE
            ),
            record_id=document.document_id,
            digest_sha256=sha256(payload).hexdigest(),
        )


class AtomicMarkdownReader:
    """Independent root-confined capability for verifying persisted Markdown bytes."""

    def __init__(self, *, root: Path) -> None:
        self._root = root

    def read_back(self, document_id: str) -> bytes | None:
        try:
            return read_confined(root=self._root, relative=markdown_relative_path(document_id))
        except DurabilityError:
            return None


def rendered_markdown_bytes(document: RedactedMarkdownDocument) -> bytes:
    """Return the exact deterministic bytes persisted by ``AtomicMarkdownSink``."""
    if not isinstance(document, RedactedMarkdownDocument):
        raise StorageError("invalid redacted Markdown document")
    try:
        verified = RedactedMarkdownDocument.from_canonical_bytes(document.canonical_bytes())
    except (TypeError, ValueError):
        raise StorageError("invalid redacted Markdown document") from None
    fields = {
        "document_id": verified.document_id,
        "frontmatter": verified.frontmatter,
        "logical_key": verified.logical_key,
        "privacy_decision": verified.privacy_decision.to_dict(),
        "redaction_receipt": verified.redaction_receipt.to_dict(),
    }
    return render_frontmatter(fields=fields, body=verified.body).encode("utf-8")
