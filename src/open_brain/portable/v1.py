from __future__ import annotations

import base64
import binascii
import json
import os
import shutil
from collections.abc import Iterable, Mapping
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import cast

from open_brain.core.ids import portable_canonical_json_bytes


class PortableValidationError(ValueError):
    """A Portable Brain v1 export is malformed, unsafe, or incomplete."""


PORTABLE_V1_SCHEMA_CATALOG_DIGEST = (
    "9c9965fcf808b10446218f0d7b0ba6dd6f42c53e76be2d2ba89191431ecb0076"
)
_OPERATIONAL_DIRECTORY = ".open-brain"


def validate_portable_root(root: Path) -> dict[str, object]:
    """Validate a strict, root-confined Portable Brain v1 export."""
    if root.is_symlink() or not root.is_dir():
        raise PortableValidationError("Portable root must be a real directory")
    try:
        root = root.resolve(strict=True)
    except OSError as error:
        raise PortableValidationError("Portable root cannot be resolved") from error
    _reject_symlinks(root)
    manifest_path = root / "portable-manifest.json"
    manifest = _load_canonical_json(manifest_path)
    if not isinstance(manifest, dict):
        raise PortableValidationError("manifest must be an object")
    _require_manifest_shape(manifest)
    entries = cast(list[object], manifest["files"])
    previous_path: str | None = None
    declared: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise PortableValidationError("manifest entry must be an object")
        path = entry.get("path")
        digest = entry.get("sha256")
        if not isinstance(path, str) or not isinstance(digest, str):
            raise PortableValidationError("manifest entry is malformed")
        _validate_relative_path(path)
        if previous_path is not None and path <= previous_path:
            raise PortableValidationError("manifest paths must be sorted and unique")
        previous_path = path
        declared.add(path)
        target = root.joinpath(*PurePosixPath(path).parts)
        if target.is_symlink() or not target.is_file():
            raise PortableValidationError("manifest file is missing or not regular")
        if sha256(target.read_bytes()).hexdigest() != digest:
            raise PortableValidationError("manifest checksum mismatch")
        _validate_blob_address(path, digest)
    actual = {
        path.relative_to(root).as_posix()
        for path in _portable_files(root)
        if path.name != "portable-manifest.json"
    }
    if declared != actual:
        raise PortableValidationError("manifest does not describe the portable root exactly")
    _validate_semantics(root, manifest)
    return manifest


def export_portable_tree(source: Path, destination: Path) -> None:
    """Copy a validated export exactly, excluding all operational state."""
    manifest = validate_portable_root(source)
    if destination.exists():
        raise PortableValidationError("export destination already exists")
    destination.mkdir(parents=True)
    entries = cast(list[Mapping[str, object]], manifest["files"])
    for entry in entries:
        path = cast(str, entry["path"])
        target = destination.joinpath(*PurePosixPath(path).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / path, target)
    shutil.copyfile(source / "portable-manifest.json", destination / "portable-manifest.json")
    validate_portable_root(destination)


def _load_canonical_json(path: Path) -> object:
    try:
        data = path.read_bytes()
        value = json.loads(data)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PortableValidationError("invalid Portable JSON") from error
    if portable_canonical_json_bytes(value) != data:
        raise PortableValidationError("Portable JSON is not canonical")
    return value


def _require_manifest_shape(manifest: Mapping[str, object]) -> None:
    required = {
        "compatibility",
        "contract_version",
        "created_at",
        "export_id",
        "files",
        "layout_version",
        "schema_catalog_digest",
        "schema_version",
        "tenant_id",
    }
    if (
        set(manifest) != required
        or manifest["layout_version"] != 1
        or manifest["schema_version"] != 1
    ):
        raise PortableValidationError("unsupported manifest shape")
    if manifest["contract_version"] != "1":
        raise PortableValidationError("unsupported Portable contract version")
    compatibility = manifest["compatibility"]
    if not isinstance(compatibility, dict) or compatibility != {
        "maximum_contract_version": "1",
        "minimum_contract_version": "1",
    }:
        raise PortableValidationError("incompatible Portable contract range")
    if not isinstance(manifest["files"], list) or not manifest["files"]:
        raise PortableValidationError("manifest files are required")
    for name in ("export_id", "tenant_id"):
        if not isinstance(manifest[name], str) or not manifest[name]:
            raise PortableValidationError("manifest identity is malformed")
    if manifest["schema_catalog_digest"] != PORTABLE_V1_SCHEMA_CATALOG_DIGEST:
        raise PortableValidationError("Portable schema catalog digest mismatch")


def _validate_relative_path(value: str) -> None:
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or "\\" in value
        or any(part in {"", ".", ".."} or part == _OPERATIONAL_DIRECTORY for part in path.parts)
        or path.as_posix() != value
    ):
        raise PortableValidationError("manifest path escapes the Portable root")


def _validate_blob_address(path: str, digest: str) -> None:
    parts = PurePosixPath(path).parts
    if parts[:3] != ("sources", "blobs", "sha256"):
        return
    if len(parts) != 5 or parts[3] != digest[:2] or parts[4] != digest:
        raise PortableValidationError("content-addressed blob path mismatch")


def _portable_files(root: Path) -> Iterable[Path]:
    for directory, names, files in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        names[:] = [name for name in names if name != _OPERATIONAL_DIRECTORY]
        for name in files:
            path = directory_path / name
            if path.is_file() and not path.is_symlink():
                yield path


def _reject_symlinks(root: Path) -> None:
    for directory, names, files in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        for name in [*names, *files]:
            if (directory_path / name).is_symlink():
                raise PortableValidationError("Portable exports must not contain symlinks")


def _validate_semantics(root: Path, manifest: Mapping[str, object]) -> None:
    tenant_id = _required_string(manifest, "tenant_id", "manifest")
    receipts: dict[str, bytes] = {}
    batches = _validate_batches(root, tenant_id)
    captures = _validate_captures(root, tenant_id, batches, receipts)
    proposals, proposal_bytes = _validate_proposals(root, tenant_id, captures, receipts)
    decisions = _validate_decisions(root, tenant_id, proposals, proposal_bytes, receipts)
    _validate_publications(root, tenant_id, proposals, decisions)
    _validate_actions(root, tenant_id, proposals, decisions, receipts)


def _json_records(root: Path, relative: str, label: str) -> list[dict[str, object]]:
    directory = root / relative
    if not directory.exists():
        return []
    if not directory.is_dir():
        raise PortableValidationError(f"{label} directory is malformed")
    return [
        _object(_load_canonical_json(path), label) for path in sorted(directory.rglob("*.json"))
    ]


def _object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise PortableValidationError(f"{label} must be an object")
    return cast(dict[str, object], value)


def _required_string(value: Mapping[str, object], key: str, label: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise PortableValidationError(f"{label} {key} is malformed")
    return item


def _required_list(value: Mapping[str, object], key: str, label: str) -> list[object]:
    item = value.get(key)
    if not isinstance(item, list):
        raise PortableValidationError(f"{label} {key} is malformed")
    return cast(list[object], item)


def _canonical_digest(value: object, label: str) -> str:
    try:
        return sha256(portable_canonical_json_bytes(value)).hexdigest()
    except (TypeError, ValueError) as error:
        raise PortableValidationError(f"{label} is not strict Portable JSON") from error


def _decode_base64(value: object, label: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise PortableValidationError(f"{label} bytes are malformed")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as error:
        raise PortableValidationError(f"{label} base64 is malformed") from error


def _verify_encoded_digest(
    value: Mapping[str, object], bytes_key: str, digest_key: str, label: str
) -> bytes:
    data = _decode_base64(value.get(bytes_key), label)
    if sha256(data).hexdigest() != value.get(digest_key):
        raise PortableValidationError(f"{label} digest mismatch")
    return data


def _validate_role_binding(record: Mapping[str, object], tenant_id: str, label: str) -> None:
    actor_id = _required_string(record, "actor_id", label)
    if record.get("tenant_id") != tenant_id:
        raise PortableValidationError(f"{label} tenant binding mismatch")
    claim = _object(record.get("role_claim"), f"{label} role claim")
    if claim.get("tenant_id") != tenant_id or claim.get("actor_id") != actor_id:
        raise PortableValidationError(f"{label} role claim binding mismatch")
    capabilities = claim.get("capabilities")
    if not isinstance(capabilities, list) or any(
        not isinstance(capability, str) for capability in capabilities
    ):
        raise PortableValidationError(f"{label} role claim capabilities are malformed")
    capability_names = cast(list[str], capabilities)
    if capability_names != sorted(set(capability_names)):
        raise PortableValidationError(f"{label} role claim capabilities must be sorted and unique")


def _validate_privacy(record: Mapping[str, object], label: str) -> None:
    privacy = _object(record.get("privacy"), f"{label} privacy")
    authority = _object(privacy.get("authority"), f"{label} privacy authority")
    if privacy.get("tier") in {"secret", "unknown"} and (
        authority.get("cloud") is True or authority.get("external_egress") is True
    ):
        raise PortableValidationError(f"{label} privacy authority exceeds its tier")


def _validate_receipt(
    value: object,
    *,
    subject_id: str,
    receipts: dict[str, bytes],
    label: str,
    expected_kind: str | None = None,
    expected_payload: Mapping[str, object] | None = None,
) -> dict[str, object]:
    receipt = _object(value, label)
    receipt_id = _required_string(receipt, "receipt_id", label)
    if receipt.get("subject_id") != subject_id:
        raise PortableValidationError(f"{label} subject binding mismatch")
    if expected_kind is not None and receipt.get("kind") != expected_kind:
        raise PortableValidationError(f"{label} kind binding mismatch")
    payload = _object(receipt.get("payload"), f"{label} payload")
    if receipt.get("sha256") != _canonical_digest(payload, f"{label} payload"):
        raise PortableValidationError(f"{label} receipt digest mismatch")
    if expected_payload is not None and payload != dict(expected_payload):
        raise PortableValidationError(f"{label} payload binding mismatch")
    try:
        receipt_bytes = portable_canonical_json_bytes(receipt)
    except (TypeError, ValueError) as error:
        raise PortableValidationError(f"{label} is not strict Portable JSON") from error
    previous = receipts.get(receipt_id)
    if previous is not None and previous != receipt_bytes:
        raise PortableValidationError("receipt ID is reused with different content")
    receipts[receipt_id] = receipt_bytes
    return receipt


def _require_blob(root: Path, digest: str, label: str) -> None:
    path = root / "sources" / "blobs" / "sha256" / digest[:2] / digest
    if not path.is_file() or path.is_symlink() or sha256(path.read_bytes()).hexdigest() != digest:
        raise PortableValidationError(f"{label} blob binding mismatch")


def _validate_batches(root: Path, tenant_id: str) -> dict[tuple[str, str], dict[str, object]]:
    directory = root / "sources" / "batches"
    rows: dict[tuple[str, str], dict[str, object]] = {}
    seen_records: dict[str, tuple[str, str]] = {}
    if not directory.exists():
        return rows
    for path in sorted(directory.rglob("*.jsonl")):
        try:
            data = path.read_bytes()
        except OSError as error:
            raise PortableValidationError("batch file cannot be read") from error
        if not data or not data.endswith(b"\n"):
            raise PortableValidationError("batch JSONL must be non-empty and end in LF")
        file_batch_id: str | None = None
        for raw_line in data.splitlines(keepends=True):
            try:
                value = json.loads(raw_line[:-1])
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise PortableValidationError("batch row is invalid JSON") from error
            row = _object(value, "batch row")
            try:
                canonical_line = portable_canonical_json_bytes(row) + b"\n"
            except (TypeError, ValueError) as error:
                raise PortableValidationError("batch row is not strict Portable JSON") from error
            if canonical_line != raw_line:
                raise PortableValidationError("batch row is not canonical JSONL")
            _validate_role_binding(row, tenant_id, "batch row")
            batch_id = _required_string(row, "batch_id", "batch row")
            record_id = _required_string(row, "record_id", "batch row")
            payload = _object(row.get("payload"), "batch row payload")
            family = _required_string(payload, "family", "batch row payload")
            if family not in {"event", "measurement"} or not record_id.startswith(f"{family}_"):
                raise PortableValidationError("batch record family binding mismatch")
            if file_batch_id is None:
                file_batch_id = batch_id
            elif file_batch_id != batch_id:
                raise PortableValidationError("batch file contains multiple batch IDs")
            if record_id in seen_records:
                raise PortableValidationError("batch record ID is duplicated")
            supersedes = row.get("supersedes")
            if supersedes is not None:
                previous = seen_records.get(cast(str, supersedes))
                if previous is None or previous != (batch_id, family):
                    raise PortableValidationError(
                        "batch supersedes must reference an earlier same-family row"
                    )
            seen_records[record_id] = (batch_id, family)
            rows[(batch_id, record_id)] = payload
    return rows


def _validate_captures(
    root: Path,
    tenant_id: str,
    batches: Mapping[tuple[str, str], dict[str, object]],
    receipts: dict[str, bytes],
) -> dict[str, dict[str, object]]:
    captures: dict[str, dict[str, object]] = {}
    for capture in _json_records(root, "sources/captures", "capture"):
        _validate_role_binding(capture, tenant_id, "capture")
        _validate_privacy(capture, "capture")
        capture_id = _required_string(capture, "capture_id", "capture")
        if capture_id in captures:
            raise PortableValidationError("capture ID is duplicated")
        payload = _object(capture.get("payload"), "capture payload")
        payload_digest = _canonical_digest(payload, "capture payload")
        original = _object(capture.get("original_payload"), "capture original payload")
        original_kind = _required_string(original, "kind", "capture original payload")
        if original_kind == "inline":
            original_bytes = _verify_encoded_digest(
                original, "bytes_base64", "sha256", "capture original payload"
            )
            original_digest = sha256(original_bytes).hexdigest()
        elif original_kind == "blob":
            original_digest = _required_string(original, "blob_sha256", "capture original payload")
            _require_blob(root, original_digest, "capture original payload")
        else:
            raise PortableValidationError("capture original payload kind is unsupported")
        blob_digest = payload.get("blob_sha256")
        if blob_digest is not None:
            if not isinstance(blob_digest, str):
                raise PortableValidationError("capture payload blob digest is malformed")
            _require_blob(root, blob_digest, "capture payload")
        binding = _object(capture.get("payload_binding"), "capture payload binding")
        binding_kind = _required_string(binding, "kind", "capture payload binding")
        if binding_kind == "inline":
            if binding.get("payload_sha256") != payload_digest:
                raise PortableValidationError("capture payload binding digest mismatch")
        elif binding_kind == "batch":
            batch_id = _required_string(binding, "batch_id", "capture payload binding")
            record_id = _required_string(binding, "record_id", "capture payload binding")
            batch_payload = batches.get((batch_id, record_id))
            if batch_payload is None:
                raise PortableValidationError("capture batch record binding is missing")
            if _canonical_digest(batch_payload, "batch payload") != payload_digest:
                raise PortableValidationError("capture batch payload binding mismatch")
        else:
            raise PortableValidationError("capture payload binding kind is unsupported")
        source = _object(capture.get("source"), "capture source")
        provenance = _object(capture.get("provenance"), "capture provenance")
        if source.get("reference") != provenance.get("source_ref"):
            raise PortableValidationError("capture provenance source binding mismatch")
        expected_receipt_payload = {
            "capture_id": capture_id,
            "original_payload_sha256": original_digest,
            "payload_sha256": payload_digest,
        }
        accepted = 0
        for receipt_value in _required_list(capture, "receipt_refs", "capture"):
            receipt = _validate_receipt(
                receipt_value,
                subject_id=capture_id,
                receipts=receipts,
                label="capture receipt",
            )
            if receipt.get("kind") == "capture_accepted":
                if receipt.get("payload") != expected_receipt_payload:
                    raise PortableValidationError("capture receipt payload binding mismatch")
                accepted += 1
        if accepted != 1:
            raise PortableValidationError("capture must have exactly one acceptance receipt")
        for receipt_value in _required_list(
            provenance, "transformation_receipts", "capture provenance"
        ):
            _validate_receipt(
                receipt_value,
                subject_id=capture_id,
                receipts=receipts,
                label="transformation receipt",
            )
        captures[capture_id] = capture
    return captures


def _validate_proposals(
    root: Path,
    tenant_id: str,
    captures: Mapping[str, dict[str, object]],
    receipts: dict[str, bytes],
) -> tuple[dict[str, dict[str, object]], dict[str, bytes]]:
    proposals: dict[str, dict[str, object]] = {}
    proposed_bytes: dict[str, bytes] = {}
    for proposal in _json_records(root, "history/proposals", "proposal"):
        _validate_role_binding(proposal, tenant_id, "proposal")
        _validate_privacy(proposal, "proposal")
        proposal_id = _required_string(proposal, "proposal_id", "proposal")
        if proposal_id in proposals:
            raise PortableValidationError("proposal ID is duplicated")
        content = _object(proposal.get("proposed_content"), "proposal content")
        content_bytes = _verify_encoded_digest(
            content, "bytes_base64", "sha256", "proposal content"
        )
        expected_payload = {
            "proposal_id": proposal_id,
            "proposed_content_sha256": content["sha256"],
        }
        _validate_receipt(
            proposal.get("expected_receipt"),
            subject_id=proposal_id,
            receipts=receipts,
            label="proposal expected receipt",
            expected_kind="proposal_created",
            expected_payload=expected_payload,
        )
        capture_ids = _required_list(proposal, "capture_ids", "proposal")
        if any(not isinstance(item, str) or item not in captures for item in capture_ids):
            raise PortableValidationError("proposal capture binding is missing")
        for evidence_value in _required_list(proposal, "evidence", "proposal"):
            evidence = _object(evidence_value, "proposal evidence")
            capture_id = _required_string(evidence, "capture_id", "proposal evidence")
            excerpt = _required_string(evidence, "excerpt", "proposal evidence")
            if capture_id not in capture_ids or capture_id not in captures:
                raise PortableValidationError("proposal evidence capture binding is missing")
            if evidence.get("sha256") != sha256(excerpt.encode("utf-8")).hexdigest():
                raise PortableValidationError("proposal evidence digest mismatch")
        proposals[proposal_id] = proposal
        proposed_bytes[proposal_id] = content_bytes
    for proposal_id, proposal in proposals.items():
        sibling_context = _object(proposal.get("sibling_context"), "proposal sibling context")
        siblings = _required_list(sibling_context, "proposal_ids", "proposal sibling context")
        if (
            any(not isinstance(item, str) or item not in proposals for item in siblings)
            or proposal_id not in siblings
            or cast(list[str], siblings) != sorted(set(cast(list[str], siblings)))
        ):
            raise PortableValidationError("proposal sibling binding mismatch")
        sibling_set = set(cast(list[str], siblings))
        for sibling_id in sibling_set:
            sibling = proposals[sibling_id]
            other_context = _object(sibling.get("sibling_context"), "proposal sibling context")
            if (
                set(
                    cast(
                        list[str],
                        _required_list(other_context, "proposal_ids", "proposal sibling context"),
                    )
                )
                != sibling_set
            ):
                raise PortableValidationError("proposal sibling binding is asymmetric")
    return proposals, proposed_bytes


def _decision_terminal_payload(
    decision: Mapping[str, object], edited_content_sha256: str | None
) -> dict[str, object]:
    return {
        "decision_id": decision.get("decision_id"),
        "edited_content_sha256": edited_content_sha256,
        "expected_state_digest": decision.get("expected_state_digest"),
        "outcome": decision.get("outcome"),
        "proposal_id": decision.get("proposal_id"),
    }


def _validate_decisions(
    root: Path,
    tenant_id: str,
    proposals: Mapping[str, dict[str, object]],
    proposed_bytes: Mapping[str, bytes],
    receipts: dict[str, bytes],
) -> dict[str, tuple[dict[str, object], bytes | None]]:
    decisions: dict[str, tuple[dict[str, object], bytes | None]] = {}
    decided_proposals: set[str] = set()
    for decision in _json_records(root, "history/decisions", "decision"):
        _validate_role_binding(decision, tenant_id, "decision")
        decision_id = _required_string(decision, "decision_id", "decision")
        proposal_id = _required_string(decision, "proposal_id", "decision")
        if decision_id in decisions:
            raise PortableValidationError("decision ID is duplicated")
        if proposal_id in decided_proposals:
            raise PortableValidationError("proposal has multiple terminal decisions")
        proposal = proposals.get(proposal_id)
        if proposal is None:
            raise PortableValidationError("decision proposal binding is missing")
        expected_receipt = _validate_receipt(
            decision.get("expected_receipt"),
            subject_id=proposal_id,
            receipts=receipts,
            label="decision expected receipt",
            expected_kind="proposal_created",
        )
        if expected_receipt != proposal.get("expected_receipt"):
            raise PortableValidationError("decision expected receipt binding mismatch")
        expected_state_digest = _canonical_digest(proposal, "proposal state")
        if decision.get("expected_state_digest") != expected_state_digest:
            raise PortableValidationError("decision proposal state digest mismatch")
        outcome = _required_string(decision, "outcome", "decision")
        edited_value = decision.get("edited_content")
        edited_digest: str | None = None
        if outcome == "edited":
            edited = _object(edited_value, "decision edited content")
            effective_bytes = _verify_encoded_digest(
                edited, "bytes_base64", "sha256", "decision edited content"
            )
            edited_digest = _required_string(edited, "sha256", "decision edited content")
        elif outcome == "approved":
            if edited_value is not None:
                raise PortableValidationError("approved decision has edited content")
            effective_bytes = proposed_bytes[proposal_id]
        elif outcome == "rejected":
            if edited_value is not None:
                raise PortableValidationError("rejected decision has edited content")
            effective_bytes = None
        else:
            raise PortableValidationError("decision outcome is unsupported")
        terminal_payload = _decision_terminal_payload(decision, edited_digest)
        if decision.get("terminal_digest") != _canonical_digest(
            terminal_payload, "decision terminal state"
        ):
            raise PortableValidationError("decision terminal digest mismatch")
        decisions[decision_id] = (decision, effective_bytes)
        decided_proposals.add(proposal_id)
    return decisions


def _validate_publications(
    root: Path,
    tenant_id: str,
    proposals: Mapping[str, dict[str, object]],
    decisions: Mapping[str, tuple[dict[str, object], bytes | None]],
) -> None:
    publication_ids: set[str] = set()
    published_decisions: set[str] = set()
    for publication in _json_records(root, "history/publications", "publication"):
        _validate_role_binding(publication, tenant_id, "publication")
        publication_id = _required_string(publication, "publication_id", "publication")
        decision_id = _required_string(publication, "decision_id", "publication")
        if publication_id in publication_ids or decision_id in published_decisions:
            raise PortableValidationError("publication identity is duplicated")
        decision_entry = decisions.get(decision_id)
        if decision_entry is None:
            raise PortableValidationError("publication decision binding is missing")
        decision, effective_bytes = decision_entry
        proposal_id = _required_string(decision, "proposal_id", "decision")
        proposal = proposals[proposal_id]
        if proposal.get("proposed_kind") != "page_update" or effective_bytes is None:
            raise PortableValidationError("publication decision is not publishable")
        published_bytes = _verify_encoded_digest(
            publication,
            "published_bytes_base64",
            "published_sha256",
            "publication bytes",
        )
        if published_bytes != effective_bytes:
            raise PortableValidationError("publication decision content binding mismatch")
        published_path = _required_string(publication, "published_path", "publication")
        _validate_relative_path(published_path)
        if not published_path.startswith("content/"):
            raise PortableValidationError("publication path is outside content")
        target = root.joinpath(*PurePosixPath(published_path).parts)
        if not target.is_file() or target.is_symlink() or target.read_bytes() != published_bytes:
            raise PortableValidationError("publication path content binding mismatch")
        publication_ids.add(publication_id)
        published_decisions.add(decision_id)


def _validate_actions(
    root: Path,
    tenant_id: str,
    proposals: Mapping[str, dict[str, object]],
    decisions: Mapping[str, tuple[dict[str, object], bytes | None]],
    receipts: dict[str, bytes],
) -> None:
    action_ids: set[str] = set()
    action_decisions: set[str] = set()
    for action in _json_records(root, "history/actions", "action"):
        _validate_role_binding(action, tenant_id, "action")
        action_id = _required_string(action, "action_id", "action")
        decision_id = _required_string(action, "decision_id", "action")
        proposal_id = _required_string(action, "proposal_id", "action")
        if action_id in action_ids or decision_id in action_decisions:
            raise PortableValidationError("action identity is duplicated")
        decision_entry = decisions.get(decision_id)
        proposal = proposals.get(proposal_id)
        if decision_entry is None or proposal is None:
            raise PortableValidationError("action review-chain binding is missing")
        decision, effective_bytes = decision_entry
        if (
            decision.get("proposal_id") != proposal_id
            or proposal.get("proposed_kind") != "action"
            or effective_bytes is None
        ):
            raise PortableValidationError("action decision binding mismatch")
        request = _object(action.get("action_request"), "action request")
        result = _object(action.get("action_result"), "action result")
        request_digest = _canonical_digest(request, "action request")
        result_digest = _canonical_digest(result, "action result")
        if action.get("action_request_sha256") != request_digest:
            raise PortableValidationError("action request digest mismatch")
        if action.get("action_result_sha256") != result_digest:
            raise PortableValidationError("action result digest mismatch")
        try:
            request_bytes = portable_canonical_json_bytes(request)
        except (TypeError, ValueError) as error:
            raise PortableValidationError("action request is not strict Portable JSON") from error
        if request_bytes != effective_bytes:
            raise PortableValidationError("action decision request binding mismatch")
        approval_payload = {
            "action_id": action_id,
            "action_request_sha256": request_digest,
            "decision_id": decision_id,
        }
        _validate_receipt(
            action.get("approval_receipt"),
            subject_id=action_id,
            receipts=receipts,
            label="action approval receipt",
            expected_kind="external_action",
            expected_payload=approval_payload,
        )
        action_ids.add(action_id)
        action_decisions.add(decision_id)
