from __future__ import annotations

import base64
import copy
import json
import os
from collections.abc import Callable, Mapping
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest
from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]
from referencing import Registry, Resource

from open_brain.portable import (
    PORTABLE_V1_SCHEMA_CATALOG_DIGEST,
    PortableValidationError,
    export_portable_tree,
    portable_canonical_json_bytes,
    validate_portable_root,
)
from open_brain.storage.markdown import parse_markdown

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = REPOSITORY_ROOT / "schemas/portable-brain/v1"
FIXTURE_ROOT = REPOSITORY_ROOT / "tests/fixtures/portable-brain/v1"
_FORMAT_CHECKER = FormatChecker()
_DIGEST = "0" * 64
TENANT = "tenant_123e4567-e89b-42d3-a456-426614174000"
ACTOR = "actor_123e4567-e89b-42d3-a456-426614174001"
SPACE = "space_123e4567-e89b-42d3-a456-426614174004"
CAPTURE = "capture_123e4567-e89b-42d3-a456-426614174100"
PAGE_PROPOSAL = "proposal_123e4567-e89b-42d3-a456-426614174008"
ACTION_PROPOSAL = "proposal_123e4567-e89b-42d3-a456-426614174018"
PAGE_DECISION = "decision_123e4567-e89b-42d3-a456-426614174009"
ACTION_DECISION = "decision_123e4567-e89b-42d3-a456-426614174019"
PAGE_ID = "page_123e4567-e89b-42d3-a456-426614174005"
BLOB_BYTES = b"Synthetic Portable Brain blob.\n"
BLOB_DIGEST = sha256(BLOB_BYTES).hexdigest()


def _schemas() -> dict[str, dict[str, object]]:
    return {
        path.name: cast(dict[str, object], json.loads(path.read_bytes()))
        for path in sorted(SCHEMA_ROOT.glob("*.json"))
    }


def _cases() -> dict[str, list[str]]:
    return cast(dict[str, list[str]], json.loads((FIXTURE_ROOT / "cases.json").read_bytes()))


def _validator(name: str) -> Draft202012Validator:
    schemas = _schemas()
    registry = Registry().with_resources(
        (str(schema["$id"]), Resource.from_contents(schema)) for schema in schemas.values()
    )
    return Draft202012Validator(schemas[name], registry=registry, format_checker=_FORMAT_CHECKER)


def _schema_catalog_digest() -> str:
    catalog = {
        path.name: sha256(path.read_bytes()).hexdigest()
        for path in sorted(SCHEMA_ROOT.glob("*.json"))
    }
    return sha256(portable_canonical_json_bytes(catalog)).hexdigest()


def _assert_valid(name: str, value: object) -> None:
    errors = sorted(_validator(name).iter_errors(value), key=str)
    assert not errors, "\n".join(error.message for error in errors)


def _claim() -> dict[str, object]:
    return {
        "actor_id": ACTOR,
        "capabilities": ["capture.accept", "space.write"],
        "role_claim_id": "role_claim_123e4567-e89b-42d3-a456-426614174003",
        "role_id": "role_123e4567-e89b-42d3-a456-426614174002",
        "tenant_id": TENANT,
    }


def _receipt(
    kind: str,
    subject_id: str,
    payload: Mapping[str, object],
    suffix: str,
) -> dict[str, object]:
    receipt_payload = dict(payload)
    return {
        "kind": kind,
        "payload": receipt_payload,
        "receipt_id": f"receipt_123e4567-e89b-42d3-a456-426614174{suffix}",
        "recorded_at": "2026-08-30T12:00:00Z",
        "sha256": sha256(portable_canonical_json_bytes(receipt_payload)).hexdigest(),
        "subject_id": subject_id,
    }


def _privacy() -> dict[str, object]:
    return {
        "authority": {"cloud": False, "external_egress": False},
        "confirmation_ref": None,
        "policy_version": "privacy-v1",
        "reason": "personal_local_only",
        "tier": "personal",
    }


def _trust() -> dict[str, object]:
    return {
        "assessed_at": "2026-08-30T12:00:00Z",
        "assessor_actor_id": ACTOR,
        "label": "owner",
        "reason": "owner supplied synthetic fixture",
    }


def _payload(family: str) -> dict[str, object]:
    if family == "text":
        return {"family": "text", "text": "Portable Brain synthetic text."}
    if family == "reference_or_file":
        return {
            "blob_sha256": BLOB_DIGEST,
            "family": "reference_or_file",
            "file_name": "fixture.txt",
            "kind": "file",
            "media_type": "text/plain",
        }
    if family == "event":
        return {
            "attributes": [{"name": "repository", "value": "open-brain"}],
            "event_type": "commit.created",
            "family": "event",
            "occurrence_at": "2026-08-30T12:00:00Z",
        }
    return {
        "dimensions": [{"name": "source", "value": "synthetic"}],
        "family": "measurement",
        "occurrence_at": "2026-08-30T12:01:00Z",
        "unit": "kg",
        "value": "0.5",
    }


def _capture(family: str, number: int) -> dict[str, object]:
    payload = _payload(family)
    capture_id = f"capture_123e4567-e89b-42d3-a456-4266141741{number:02d}"
    original_bytes = portable_canonical_json_bytes(payload)
    payload_digest = sha256(portable_canonical_json_bytes(payload)).hexdigest()
    if family == "reference_or_file":
        original_payload: dict[str, object] = {"blob_sha256": BLOB_DIGEST, "kind": "blob"}
        original_digest = BLOB_DIGEST
    else:
        original_payload = {
            "bytes_base64": base64.b64encode(original_bytes).decode("ascii"),
            "kind": "inline",
            "sha256": sha256(original_bytes).hexdigest(),
        }
        original_digest = sha256(original_bytes).hexdigest()
    if family == "event":
        payload_binding: dict[str, object] = {
            "batch_id": "batch_123e4567-e89b-42d3-a456-426614174006",
            "kind": "batch",
            "record_id": "event_123e4567-e89b-42d3-a456-426614174060",
        }
    elif family == "measurement":
        payload_binding = {
            "batch_id": "batch_123e4567-e89b-42d3-a456-426614174007",
            "kind": "batch",
            "record_id": "measurement_123e4567-e89b-42d3-a456-426614174070",
        }
    else:
        payload_binding = {"kind": "inline", "payload_sha256": payload_digest}
    receipt_payload = {
        "capture_id": capture_id,
        "original_payload_sha256": original_digest,
        "payload_sha256": payload_digest,
    }
    return {
        "accepted_at": f"2026-08-30T12:0{number}:00Z",
        "actor_id": ACTOR,
        "capture_id": capture_id,
        "capture_why": "synthetic fixture" if number == 0 else None,
        "intent": "idea" if number == 0 else None,
        "original_payload": original_payload,
        "payload": payload,
        "payload_binding": payload_binding,
        "payload_schema_version": 1,
        "privacy": _privacy(),
        "provenance": {
            "content_origin": "owner_authored",
            "owner_context": "owner_authored",
            "source_ref": "urn:example.invalid:portable-fixture",
            "transformation_receipts": [],
        },
        "receipt_refs": [_receipt("capture_accepted", capture_id, receipt_payload, f"11{number}")],
        "role_claim": _claim(),
        "schema_version": 1,
        "source": {"origin": "owner", "reference": "urn:example.invalid:portable-fixture"},
        "space_id": SPACE if number != 1 else None,
        "tenant_id": TENANT,
        "trust": _trust(),
    }


def _action_request() -> dict[str, object]:
    return {"kind": "external_message", "target": "https://example.invalid/action"}


def _proposal(
    proposal_id: str = PAGE_PROPOSAL,
    proposed_kind: str = "page_update",
) -> dict[str, object]:
    proposed_bytes = (
        portable_canonical_json_bytes(_action_request())
        if proposed_kind == "action"
        else b"# Proposed synthetic page\n"
    )
    proposed_digest = sha256(proposed_bytes).hexdigest()
    receipt_payload = {
        "proposal_id": proposal_id,
        "proposed_content_sha256": proposed_digest,
    }
    receipt_suffix = "120" if proposal_id == PAGE_PROPOSAL else "121"
    evidence = "synthetic evidence"
    return {
        "actor_id": ACTOR,
        "capture_ids": [CAPTURE],
        "evidence": [
            {
                "capture_id": CAPTURE,
                "excerpt": evidence,
                "sha256": sha256(evidence.encode()).hexdigest(),
            }
        ],
        "expected_receipt": _receipt(
            "proposal_created", proposal_id, receipt_payload, receipt_suffix
        ),
        "privacy": _privacy(),
        "proposal_id": proposal_id,
        "proposed_content": {
            "bytes_base64": base64.b64encode(proposed_bytes).decode("ascii"),
            "media_type": "application/json" if proposed_kind == "action" else "text/markdown",
            "sha256": proposed_digest,
        },
        "proposed_kind": proposed_kind,
        "recorded_at": "2026-08-30T12:05:00Z",
        "role_claim": _claim(),
        "schema_version": 1,
        "sibling_context": {"proposal_ids": [PAGE_PROPOSAL, ACTION_PROPOSAL]},
        "space_id": SPACE,
        "status": "pending",
        "supplied_reason": "synthetic review evidence",
        "tenant_id": TENANT,
        "trust": _trust(),
    }


def _page_frontmatter() -> dict[str, object]:
    return {
        "actor_id": ACTOR,
        "modified_at": "2026-08-30T12:10:00Z",
        "page_id": PAGE_ID,
        "privacy": _privacy(),
        "provenance": [CAPTURE],
        "role_claim": _claim(),
        "schema_version": 1,
        "space_id": SPACE,
        "status": "active",
        "tenant_id": TENANT,
        "title": "Synthetic",
        "trust": "owner",
    }


def _page_bytes() -> bytes:
    frontmatter = _page_frontmatter()
    return (
        "---\n"
        + "\n".join(
            f"{key}: {json.dumps(value, separators=(',', ':'))}"
            for key, value in sorted(frontmatter.items())
        )
        + "\n---\n\n# Synthetic\n"
    ).encode()


def _terminal_payload(
    *,
    decision_id: str,
    edited_content_sha256: str | None,
    expected_state_digest: str,
    outcome: str,
    proposal_id: str,
) -> dict[str, object]:
    return {
        "decision_id": decision_id,
        "edited_content_sha256": edited_content_sha256,
        "expected_state_digest": expected_state_digest,
        "outcome": outcome,
        "proposal_id": proposal_id,
    }


def _decision(
    proposal: dict[str, object] | None = None,
    decision_id: str = PAGE_DECISION,
    outcome: str = "edited",
) -> dict[str, object]:
    if proposal is None:
        proposal = _proposal()
    proposal_id = cast(str, proposal["proposal_id"])
    expected_state_digest = sha256(portable_canonical_json_bytes(proposal)).hexdigest()
    edited_bytes = _page_bytes() if outcome == "edited" else None
    edited_content = (
        {
            "bytes_base64": base64.b64encode(edited_bytes).decode("ascii"),
            "sha256": sha256(edited_bytes).hexdigest(),
        }
        if edited_bytes is not None
        else None
    )
    edited_digest = cast(dict[str, object], edited_content)["sha256"] if edited_content else None
    terminal_payload = _terminal_payload(
        decision_id=decision_id,
        edited_content_sha256=cast(str | None, edited_digest),
        expected_state_digest=expected_state_digest,
        outcome=outcome,
        proposal_id=proposal_id,
    )
    return {
        "actor_id": ACTOR,
        "decision_id": decision_id,
        "edited_content": edited_content,
        "expected_receipt": copy.deepcopy(proposal["expected_receipt"]),
        "expected_state_digest": expected_state_digest,
        "outcome": outcome,
        "proposal_id": proposal_id,
        "recorded_at": "2026-08-30T12:06:00Z",
        "role_claim": _claim(),
        "schema_version": 1,
        "terminal_digest": sha256(portable_canonical_json_bytes(terminal_payload)).hexdigest(),
        "tenant_id": TENANT,
    }


def _publication() -> dict[str, object]:
    published_bytes = _page_bytes()
    return {
        "actor_id": ACTOR,
        "decision_id": PAGE_DECISION,
        "page_id": PAGE_ID,
        "publication_id": "publication_123e4567-e89b-42d3-a456-42661417400a",
        "published_bytes_base64": base64.b64encode(published_bytes).decode("ascii"),
        "published_path": "content/spaces/studio/notes/synthetic.md",
        "published_sha256": sha256(published_bytes).hexdigest(),
        "recorded_at": "2026-08-30T12:10:00Z",
        "role_claim": _claim(),
        "schema_version": 1,
        "tenant_id": TENANT,
    }


def _action() -> dict[str, object]:
    request = _action_request()
    result = {"status": "not_sent"}
    approval_payload = {
        "action_id": "action_123e4567-e89b-42d3-a456-42661417400b",
        "action_request_sha256": sha256(portable_canonical_json_bytes(request)).hexdigest(),
        "decision_id": ACTION_DECISION,
    }
    return {
        "action_id": "action_123e4567-e89b-42d3-a456-42661417400b",
        "action_request": request,
        "action_request_sha256": sha256(portable_canonical_json_bytes(request)).hexdigest(),
        "action_result": result,
        "action_result_sha256": sha256(portable_canonical_json_bytes(result)).hexdigest(),
        "actor_id": ACTOR,
        "approval_receipt": _receipt(
            "external_action",
            "action_123e4567-e89b-42d3-a456-42661417400b",
            approval_payload,
            "130",
        ),
        "decision_id": ACTION_DECISION,
        "outcome": "not_executed",
        "proposal_id": ACTION_PROPOSAL,
        "recorded_at": "2026-08-30T12:11:00Z",
        "role_claim": _claim(),
        "schema_version": 1,
        "tenant_id": TENANT,
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(portable_canonical_json_bytes(value))


def _write_manifest(root: Path) -> None:
    files = []
    for path in sorted(root.rglob("*")):
        if (
            path.is_file()
            and path.name != "portable-manifest.json"
            and ".open-brain" not in path.parts
        ):
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": sha256(path.read_bytes()).hexdigest(),
                }
            )
    _write_json(
        root / "portable-manifest.json",
        {
            "compatibility": {"maximum_contract_version": "1", "minimum_contract_version": "1"},
            "contract_version": "1",
            "created_at": "2026-08-30T12:12:00Z",
            "export_id": "export_123e4567-e89b-42d3-a456-42661417400c",
            "files": files,
            "layout_version": 1,
            "schema_catalog_digest": PORTABLE_V1_SCHEMA_CATALOG_DIGEST,
            "schema_version": 1,
            "tenant_id": TENANT,
        },
    )


def _set_record_path(
    record: dict[str, object], path: tuple[str | int, ...], replacement: object
) -> None:
    current: object = record
    for part in path[:-1]:
        if isinstance(part, str):
            current = cast(dict[str, object], current)[part]
        else:
            current = cast(list[object], current)[part]
    final = path[-1]
    if isinstance(final, str):
        cast(dict[str, object], current)[final] = replacement
    else:
        cast(list[object], current)[final] = replacement


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "brain-root"
    root.mkdir(parents=True, exist_ok=True)
    (root / "brain.toml").write_text("layout_version = 1\n", encoding="utf-8")
    for number, family in enumerate(("text", "reference_or_file", "event", "measurement")):
        _write_json(
            root / f"sources/captures/2026/08/capture_{number}.json", _capture(family, number)
        )
    for family, prefix, batch in (("event", "event", "006"), ("measurement", "measurement", "007")):
        rows = []
        for number in (0, 1):
            record_id = f"{prefix}_123e4567-e89b-42d3-a456-426614174{batch[-2:]}{number}"
            rows.append(
                {
                    "actor_id": ACTOR,
                    "batch_id": f"batch_123e4567-e89b-42d3-a456-426614174{batch}",
                    "payload": _payload(family),
                    "record_id": record_id,
                    "recorded_at": f"2026-08-30T12:0{number}:00Z",
                    "role_claim": _claim(),
                    "schema_version": 1,
                    "supersedes": None
                    if number == 0
                    else f"{prefix}_123e4567-e89b-42d3-a456-426614174{batch[-2:]}0",
                    "tenant_id": TENANT,
                }
            )
        path = root / f"sources/batches/2026/08/batch_{batch}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"".join(portable_canonical_json_bytes(row) + b"\n" for row in rows))
    blob = root / f"sources/blobs/sha256/{BLOB_DIGEST[:2]}/{BLOB_DIGEST}"
    blob.parent.mkdir(parents=True, exist_ok=True)
    blob.write_bytes(BLOB_BYTES)
    page_proposal = _proposal()
    action_proposal = _proposal(ACTION_PROPOSAL, "action")
    page_decision = _decision(page_proposal)
    action_decision = _decision(action_proposal, ACTION_DECISION, "approved")
    _write_json(root / "history/proposals/2026/08/proposal.json", page_proposal)
    _write_json(root / "history/proposals/2026/08/proposal-action.json", action_proposal)
    _write_json(root / "history/decisions/2026/08/decision.json", page_decision)
    _write_json(root / "history/decisions/2026/08/decision-action.json", action_decision)
    _write_json(root / "history/publications/2026/08/publication.json", _publication())
    _write_json(root / "history/actions/2026/08/action.json", _action())
    content = root / "content/spaces/studio/notes/synthetic.md"
    content.parent.mkdir(parents=True, exist_ok=True)
    content.write_bytes(_page_bytes())
    space = root / "content/spaces/studio/_space.md"
    space.write_text(
        "---\n"
        + "\n".join(
            f"{key}: {json.dumps(value, separators=(',', ':'))}"
            for key, value in sorted(
                {
                    "actor_id": ACTOR,
                    "name": "Studio",
                    "role_claim": _claim(),
                    "schema_version": 1,
                    "slug": "studio",
                    "space_id": SPACE,
                    "tenant_id": TENANT,
                }.items()
            )
        )
        + "\n---\n\nSynthetic space definition.\n",
        encoding="utf-8",
    )
    _write_manifest(root)
    return root


def test_every_schema_is_draft_2020_12_closed_and_local() -> None:
    schemas = _schemas()
    assert len(schemas) == 14
    for schema in schemas.values():
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert str(schema["$id"]).startswith("urn:open-brain:portable-brain:v1:")
        Draft202012Validator.check_schema(schema)
    assert _schema_catalog_digest() == PORTABLE_V1_SCHEMA_CATALOG_DIGEST


def test_capture_is_lossless_snake_case_and_each_required_field_is_enforced() -> None:
    capture = _capture("text", 0)
    _assert_valid("capture.json", capture)
    assert {"intent", "original_payload", "privacy", "provenance", "receipt_refs", "trust"} <= set(
        capture
    )
    for field in tuple(capture):
        incomplete = copy.deepcopy(capture)
        incomplete.pop(field)
        assert list(_validator("capture.json").iter_errors(incomplete)), field
    for container in ("privacy", "provenance", "trust"):
        nested_value = cast(dict[str, object], capture[container])
        for field in tuple(nested_value):
            incomplete = copy.deepcopy(capture)
            cast(dict[str, object], incomplete[container]).pop(field)
            assert list(_validator("capture.json").iter_errors(incomplete)), f"{container}:{field}"
    original_payload = cast(dict[str, object], capture["original_payload"])
    original_bytes = base64.b64decode(cast(str, original_payload["bytes_base64"]))
    payload_digest = sha256(original_bytes).hexdigest()
    assert original_bytes == portable_canonical_json_bytes(capture["payload"])
    assert original_payload["sha256"] == payload_digest
    assert cast(dict[str, object], capture["payload_binding"])["payload_sha256"] == payload_digest


@pytest.mark.parametrize("value", _cases()["measurement_positive_values"])
def test_measurement_accepts_canonical_values_at_or_below_128_digits(value: str) -> None:
    measurement = _payload("measurement")
    measurement["value"] = value
    _assert_valid("measurement.json", measurement)


@pytest.mark.parametrize("value", _cases()["measurement_negative_values"])
def test_measurement_rejects_noncanonical_or_129_digit_values(value: str) -> None:
    measurement = _payload("measurement")
    measurement["value"] = value
    assert list(_validator("measurement.json").iter_errors(measurement))


def test_batch_rows_bind_payload_record_and_supersedes_to_one_family() -> None:
    event = {
        "actor_id": ACTOR,
        "batch_id": "batch_123e4567-e89b-42d3-a456-426614174006",
        "payload": _payload("event"),
        "record_id": "event_123e4567-e89b-42d3-a456-426614174200",
        "recorded_at": "2026-08-30T12:00:00Z",
        "role_claim": _claim(),
        "schema_version": 1,
        "supersedes": None,
        "tenant_id": TENANT,
    }
    _assert_valid("batch-row.json", event)
    bad_id = copy.deepcopy(event)
    bad_id["record_id"] = "measurement_123e4567-e89b-42d3-a456-426614174200"
    bad_supersedes = copy.deepcopy(event)
    bad_supersedes["supersedes"] = "measurement_123e4567-e89b-42d3-a456-426614174200"
    assert list(_validator("batch-row.json").iter_errors(bad_id))
    assert list(_validator("batch-row.json").iter_errors(bad_supersedes))


@pytest.mark.parametrize(
    ("name", "factory"),
    [
        ("proposal.json", _proposal),
        ("decision.json", _decision),
        ("publication.json", _publication),
        ("action.json", _action),
    ],
)
def test_review_history_requires_content_receipts_and_digests(
    name: str, factory: Callable[[], dict[str, object]]
) -> None:
    value = factory()
    _assert_valid(name, value)
    for field in tuple(value):
        incomplete = copy.deepcopy(value)
        incomplete.pop(field)
        assert list(_validator(name).iter_errors(incomplete)), f"{name}:{field}"
    if name == "action.json":
        assert (
            sha256(portable_canonical_json_bytes(value["action_request"])).hexdigest()
            == value["action_request_sha256"]
        )
        assert (
            sha256(portable_canonical_json_bytes(value["action_result"])).hexdigest()
            == value["action_result_sha256"]
        )
    elif name == "proposal.json":
        proposed = cast(dict[str, object], value["proposed_content"])
        proposed_bytes = base64.b64decode(cast(str, proposed["bytes_base64"]))
        assert sha256(proposed_bytes).hexdigest() == proposed["sha256"]
    elif name == "decision.json":
        edited = cast(dict[str, object], value["edited_content"])
        edited_bytes = base64.b64decode(cast(str, edited["bytes_base64"]))
        assert sha256(edited_bytes).hexdigest() == edited["sha256"]
        proposal = _proposal()
        assert value["expected_receipt"] == proposal["expected_receipt"]
        assert (
            value["expected_state_digest"]
            == sha256(portable_canonical_json_bytes(proposal)).hexdigest()
        )
        terminal_payload = _terminal_payload(
            decision_id=cast(str, value["decision_id"]),
            edited_content_sha256=edited["sha256"],
            expected_state_digest=value["expected_state_digest"],
            outcome=cast(str, value["outcome"]),
            proposal_id=cast(str, value["proposal_id"]),
        )
        assert (
            value["terminal_digest"]
            == sha256(portable_canonical_json_bytes(terminal_payload)).hexdigest()
        )
    elif name == "publication.json":
        published = base64.b64decode(cast(str, value["published_bytes_base64"]))
        assert sha256(published).hexdigest() == value["published_sha256"]


def test_canonical_page_frontmatter_requires_privacy(tmp_path: Path) -> None:
    root = _root(tmp_path)
    fields = dict(
        parse_markdown((root / "content/spaces/studio/notes/synthetic.md").read_bytes()).fields
    )
    _assert_valid("canonical-page-frontmatter.json", fields)
    space_fields = dict(
        parse_markdown((root / "content/spaces/studio/_space.md").read_bytes()).fields
    )
    _assert_valid("space-frontmatter.json", space_fields)
    fields.pop("privacy")
    assert list(_validator("canonical-page-frontmatter.json").iter_errors(fields))


def test_strict_json_rejects_floats_keys_and_normalized_collisions() -> None:
    with pytest.raises(ValueError, match="floats"):
        portable_canonical_json_bytes({"value": 0.5})
    with pytest.raises(ValueError, match="string object keys"):
        portable_canonical_json_bytes({1: "synthetic"})
    with pytest.raises(ValueError, match="normalized key collision"):
        portable_canonical_json_bytes({"e\u0301": 1, "é": 2})


def test_manifest_root_confinement_compatibility_and_exact_round_trip(tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / ".open-brain/state").mkdir(parents=True)
    (root / ".open-brain/state/runtime.sqlite3").write_bytes(b"runtime canary")
    manifest = validate_portable_root(root)
    _assert_valid("manifest.json", manifest)
    exported = tmp_path / "exported"
    export_portable_tree(root, exported)
    assert not (exported / ".open-brain").exists()
    assert validate_portable_root(exported) == manifest
    for path in exported.rglob("*"):
        if path.is_file():
            assert path.read_bytes() == (root / path.relative_to(exported)).read_bytes()


@pytest.mark.parametrize(
    ("case", "path"),
    [
        ("traversal", _cases()["manifest_negative_paths"][0]),
        ("absolute", _cases()["manifest_negative_paths"][1]),
        ("operational", _cases()["manifest_negative_paths"][2]),
        ("nested-operational", _cases()["manifest_negative_paths"][3]),
        ("unsorted", ""),
        ("duplicate", ""),
        ("compatibility", ""),
        ("schema-catalog", ""),
    ],
)
def test_manifest_rejects_unsafe_paths_duplicates_order_and_compatibility(
    tmp_path: Path, case: str, path: str
) -> None:
    root = _root(tmp_path)
    manifest = cast(dict[str, object], json.loads((root / "portable-manifest.json").read_bytes()))
    entries = cast(list[dict[str, object]], manifest["files"])
    if case == "unsorted":
        entries[:] = [entries[-1], entries[0]] if len(entries) > 1 else entries
    elif case == "duplicate":
        entries.append(copy.deepcopy(entries[0]))
    elif case == "compatibility":
        manifest["contract_version"] = "2"
    elif case == "schema-catalog":
        manifest["schema_catalog_digest"] = _DIGEST
    else:
        entries[0]["path"] = path
        assert list(_validator("manifest.json").iter_errors(manifest))
    _write_json(root / "portable-manifest.json", manifest)
    with pytest.raises(PortableValidationError):
        validate_portable_root(root)


def test_manifest_rejects_symlinks_and_duplicate_terminal_decisions(tmp_path: Path) -> None:
    root = _root(tmp_path)
    outside = tmp_path / "outside"
    outside.write_text("outside", encoding="utf-8")
    os.symlink(outside, root / "content/symlink.md")
    with pytest.raises(PortableValidationError, match="symlinks"):
        validate_portable_root(root)
    (root / "content/symlink.md").unlink()
    duplicate = _decision()
    duplicate["decision_id"] = "decision_123e4567-e89b-42d3-a456-42661417400d"
    _write_json(root / "history/decisions/2026/08/duplicate.json", duplicate)
    _write_manifest(root)
    with pytest.raises(PortableValidationError, match="multiple terminal"):
        validate_portable_root(root)


def test_manifest_rejects_a_symlink_root_and_allows_non_operational_state_names(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    allowed = root / "content/spaces/studio/state/notes.md"
    allowed.parent.mkdir(parents=True)
    allowed.write_text("Synthetic user state page.\n", encoding="utf-8")
    _write_manifest(root)
    validate_portable_root(root)

    linked_root = tmp_path / "linked-root"
    linked_root.symlink_to(root, target_is_directory=True)
    with pytest.raises(PortableValidationError, match="real directory"):
        validate_portable_root(linked_root)


def test_manifest_rejects_a_blob_stored_outside_its_digest_prefix(tmp_path: Path) -> None:
    root = _root(tmp_path)
    blob = next((root / "sources/blobs/sha256").rglob("*"))
    while blob.is_dir():
        blob = next(blob.rglob("*"))
    wrong = root / "sources/blobs/sha256/00" / blob.name
    wrong.parent.mkdir(parents=True)
    blob.rename(wrong)
    _write_manifest(root)

    with pytest.raises(PortableValidationError, match="blob path"):
        validate_portable_root(root)


def test_runtime_fixture_has_all_payloads_receipt_bound_routing_and_no_checked_in_operational_state(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    captures = [
        json.loads(path.read_bytes())
        for path in sorted((root / "sources/captures/2026/08").glob("*.json"))
    ]
    assert {capture["payload"]["family"] for capture in captures} == {
        "text",
        "reference_or_file",
        "event",
        "measurement",
    }
    routed = copy.deepcopy(captures[0])
    routing_payload = {"capture_id": routed["capture_id"], "route": "synthetic"}
    cast(list[object], routed["receipt_refs"]).append(
        _receipt("routing", cast(str, routed["capture_id"]), routing_payload, "140")
    )
    assert routed["receipt_refs"][-1]["kind"] == "routing"
    _assert_valid("capture.json", routed)
    assert (root / "content/spaces/studio/_space.md").is_file()
    assert ".open-brain" not in {part for path in root.rglob("*") for part in path.parts}


@pytest.mark.parametrize(
    ("case", "relative_path", "field_path", "replacement", "message"),
    [
        (
            "payload-digest",
            "sources/captures/2026/08/capture_0.json",
            ("payload_binding", "payload_sha256"),
            _DIGEST,
            "capture payload binding",
        ),
        (
            "batch-record",
            "sources/captures/2026/08/capture_2.json",
            ("payload_binding", "record_id"),
            "event_123e4567-e89b-42d3-a456-426614174999",
            "batch record",
        ),
        (
            "role-claim",
            "sources/captures/2026/08/capture_0.json",
            ("role_claim", "actor_id"),
            "actor_123e4567-e89b-42d3-a456-426614174099",
            "role claim",
        ),
        (
            "receipt",
            "sources/captures/2026/08/capture_0.json",
            ("receipt_refs", 0, "payload", "payload_sha256"),
            _DIGEST,
            "receipt digest",
        ),
        (
            "evidence",
            "history/proposals/2026/08/proposal.json",
            ("evidence", 0, "sha256"),
            _DIGEST,
            "evidence digest",
        ),
        (
            "proposal-state",
            "history/decisions/2026/08/decision.json",
            ("expected_state_digest",),
            _DIGEST,
            "proposal state",
        ),
        (
            "publication-chain",
            "history/publications/2026/08/publication.json",
            ("decision_id",),
            ACTION_DECISION,
            "publication decision",
        ),
        (
            "action-result",
            "history/actions/2026/08/action.json",
            ("action_result", "status"),
            "tampered",
            "action result digest",
        ),
    ],
)
def test_runtime_rejects_cross_record_semantic_tampering(
    tmp_path: Path,
    case: str,
    relative_path: str,
    field_path: tuple[str | int, ...],
    replacement: object,
    message: str,
) -> None:
    root = _root(tmp_path / case)
    target = root / relative_path
    record = cast(dict[str, object], json.loads(target.read_bytes()))
    _set_record_path(record, field_path, replacement)
    _write_json(target, record)
    _write_manifest(root)

    with pytest.raises(PortableValidationError, match=message):
        validate_portable_root(root)


def test_checked_in_conformance_root_is_complete_canonical_and_schema_valid(
    tmp_path: Path,
) -> None:
    root = FIXTURE_ROOT / "brain-root"
    generated = _root(tmp_path)
    fixture_files = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }
    generated_files = {
        path.relative_to(generated).as_posix(): path.read_bytes()
        for path in generated.rglob("*")
        if path.is_file()
    }
    assert fixture_files == generated_files
    manifest = validate_portable_root(root)
    _assert_valid("manifest.json", manifest)
    captures = sorted((root / "sources/captures/2026/08").glob("*.json"))
    assert len(captures) == 4
    for path in captures:
        data = path.read_bytes()
        value = json.loads(data)
        assert portable_canonical_json_bytes(value) == data
        _assert_valid("capture.json", value)
    history_schemas = {
        "actions": "action.json",
        "decisions": "decision.json",
        "proposals": "proposal.json",
        "publications": "publication.json",
    }
    expected_history_counts = {"actions": 1, "decisions": 2, "proposals": 2, "publications": 1}
    for directory, schema in history_schemas.items():
        paths = sorted((root / "history" / directory).rglob("*.json"))
        assert len(paths) == expected_history_counts[directory]
        for path in paths:
            data = path.read_bytes()
            value = json.loads(data)
            assert portable_canonical_json_bytes(value) == data
            _assert_valid(schema, value)
    for path in sorted((root / "sources/batches/2026/08").glob("*.jsonl")):
        data = path.read_bytes()
        assert data.endswith(b"\n")
        for line in data.splitlines(keepends=True):
            value = json.loads(line)
            assert portable_canonical_json_bytes(value) + b"\n" == line
            _assert_valid("batch-row.json", value)
    space = parse_markdown((root / "content/spaces/studio/_space.md").read_bytes())
    page = parse_markdown((root / "content/spaces/studio/notes/synthetic.md").read_bytes())
    _assert_valid("space-frontmatter.json", dict(space.fields))
    _assert_valid("canonical-page-frontmatter.json", dict(page.fields))
    assert not any(path.is_file() for path in (root / ".open-brain").rglob("*"))
