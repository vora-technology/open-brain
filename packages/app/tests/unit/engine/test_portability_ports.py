from __future__ import annotations

import json
import os
from collections.abc import Callable
from importlib.resources import files
from pathlib import Path

import pytest
from open_brain_engine.core.ids import portable_canonical_json_bytes
from open_brain_engine.engine import portability_ports
from open_brain_engine.engine.portability_ports import (
    LocalPortableWrites,
    LocalTenantStorage,
    local_portability_ports,
)
from open_brain_engine.storage.filesystem import RootConfinementError, WriteState
from open_brain_engine.storage.markdown import parse_markdown, render_markdown

from open_brain.profile import compile_single_user_local

FIXTURE_ROOT = Path(
    str(files("open_brain_engine.portable").joinpath("conformance/v1/brain-root"))
)


def _fixture_payload(relative: str) -> bytes:
    return (FIXTURE_ROOT / relative).read_bytes()


def _for_tenant(payload: bytes, tenant_id: str) -> bytes:
    def replace_tenant(value: object) -> object:
        if isinstance(value, dict):
            return {
                key: tenant_id if key == "tenant_id" else replace_tenant(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [replace_tenant(item) for item in value]
        return value

    if payload.endswith(b"\n"):
        return b"".join(
            portable_canonical_json_bytes(replace_tenant(json.loads(line))) + b"\n"
            for line in payload.splitlines()
        )
    return portable_canonical_json_bytes(replace_tenant(json.loads(payload)))


def _without_json_field(payload: bytes, field: str) -> bytes:
    value = json.loads(payload)
    assert isinstance(value, dict)
    del value[field]
    return portable_canonical_json_bytes(value)


def _without_markdown_field(payload: bytes, field: str) -> bytes:
    parsed = parse_markdown(payload)
    fields = dict(parsed.fields)
    del fields[field]
    return render_markdown(fields=fields, body=parsed.body).encode()


def test_local_portability_ports_are_tenant_bound_plaintext_and_validate_before_writing(
    tmp_path: Path,
) -> None:
    profile = compile_single_user_local(tmp_path / "brain")
    source_records, batches, blobs, history, storage, protection = local_portability_ports(
        profile.root,
        profile.tenant_id,
    )

    assert all(
        port.tenant_id == profile.tenant_id
        for port in (source_records, batches, blobs, history, storage, protection)
    )
    assert protection.declaration().scheme == "none"
    assert protection.declaration().encrypted is False
    assert isinstance(storage, LocalTenantStorage)
    assert not hasattr(storage, "write_portable")


def test_typed_portable_puts_validate_before_io_and_bound_duplicates_and_conflicts(
    tmp_path: Path,
) -> None:
    profile = compile_single_user_local(tmp_path / "brain")
    source_records, batches, blobs, history, storage, _ = local_portability_ports(
        profile.root,
        profile.tenant_id,
    )
    capture_path = "sources/captures/2026/08/capture_123e4567-e89b-42d3-a456-426614174100.json"
    capture = _for_tenant(_fixture_payload(capture_path), profile.tenant_id)

    with pytest.raises(ValueError, match="capture"):
        source_records.put_capture(b"{}")
    assert not (profile.root / capture_path).exists()
    assert not hasattr(storage, "write_portable")
    assert not (profile.root / capture_path).exists()

    assert source_records.put_capture(capture) is WriteState.CREATED
    assert source_records.put_capture(capture) is WriteState.ALREADY_EXISTS
    conflicting = json.loads(capture)
    conflicting["capture_why"] = "conflicting replay bytes"
    with pytest.raises(ValueError, match="conflict"):
        source_records.put_capture(portable_canonical_json_bytes(conflicting))
    assert (profile.root / capture_path).read_bytes() == capture

    batch = _for_tenant(
        _fixture_payload(
            "sources/batches/2026/08/batch_123e4567-e89b-42d3-a456-426614174006.jsonl"
        ),
        profile.tenant_id,
    )
    proposal = _for_tenant(
        _fixture_payload(
            "history/proposals/2026/08/proposal_123e4567-e89b-42d3-a456-426614174008.json"
        ),
        profile.tenant_id,
    )
    routing = _for_tenant(
        _fixture_payload(
            "history/routes/2026/08/route_123e4567-e89b-42d3-a456-426614174012.json"
        ),
        profile.tenant_id,
    )
    assert batches.put_batch(batch) is WriteState.CREATED
    assert blobs.put_blob(b"Synthetic typed blob.\n") is WriteState.CREATED
    assert history.put_history("proposal", proposal) is WriteState.CREATED
    assert history.put_history("routing", routing) is WriteState.CREATED
    with pytest.raises(ValueError, match="batch"):
        batches.put_batch(b"{}\n")
    with pytest.raises(ValueError, match="proposal"):
        history.put_history("proposal", b"{}")


def test_local_portable_inventory_rejects_preexisting_hardlinks(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    source = root / "content/spaces/studio/state/owner.md"
    source.parent.mkdir(parents=True)
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"outside Portable bytes\n")
    os.link(outside, source)

    storage = LocalTenantStorage(root=root, tenant_id="tenant_123e4567-e89b-42d3-a456-426614174000")
    with pytest.raises(ValueError, match="unsafe Portable source file"):
        list(storage.portable_files())


def test_local_portable_inventory_rejects_lstat_read_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "brain"
    source = root / "content/spaces/studio/state/owner.md"
    source.parent.mkdir(parents=True)
    storage = LocalTenantStorage(root=root, tenant_id="tenant_123e4567-e89b-42d3-a456-426614174000")
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"outside Portable bytes\n")
    source.write_bytes(b"inside Portable bytes\n")
    switched = False
    original_open_file = portability_ports._open_portable_file

    def replace_source() -> None:
        nonlocal switched
        if not switched:
            switched = True
            source.unlink()
            source.symlink_to(outside)

    def racing_open_file(directory_fd: int, name: str) -> int:
        if name == source.name:
            replace_source()
        return original_open_file(directory_fd, name)

    monkeypatch.setattr(portability_ports, "_open_portable_file", racing_open_file)

    with pytest.raises(ValueError, match="unsafe Portable source file"):
        list(storage.portable_files())
    assert outside.read_bytes() == b"outside Portable bytes\n"


def test_typed_portable_writes_validate_every_family_before_persistence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "brain"
    root.mkdir()
    tenant_id = "tenant_123e4567-e89b-42d3-a456-426614174000"
    source_records, batches, _blobs, history, _, _ = local_portability_ports(root, tenant_id)
    writes = LocalPortableWrites(root=root, tenant_id=tenant_id)

    invalid_batch = b"".join(
        _without_json_field(line, "actor_id") + b"\n"
        for line in _fixture_payload(
            "sources/batches/2026/08/batch_123e4567-e89b-42d3-a456-426614174006.jsonl"
        ).splitlines()
    )
    calls: tuple[Callable[[], object], ...] = (
        lambda: source_records.put_capture(
            _without_json_field(
                _fixture_payload(
                    "sources/captures/2026/08/capture_123e4567-e89b-42d3-a456-426614174100.json"
                ),
                "actor_id",
            )
        ),
        lambda: batches.put_batch(invalid_batch),
        lambda: history.put_history(
            "proposal",
            _without_json_field(
                _fixture_payload(
                    "history/proposals/2026/08/proposal_123e4567-e89b-42d3-a456-426614174008.json"
                ),
                "actor_id",
            ),
        ),
        lambda: history.put_history(
            "routing",
            _without_json_field(
                _fixture_payload(
                    "history/routes/2026/08/route_123e4567-e89b-42d3-a456-426614174012.json"
                ),
                "actor_id",
            ),
        ),
        lambda: history.put_history(
            "decision",
            _without_json_field(
                _fixture_payload(
                    "history/decisions/2026/08/decision_123e4567-e89b-42d3-a456-426614174009.json"
                ),
                "actor_id",
            ),
        ),
        lambda: history.put_history(
            "publication",
            _without_json_field(
                _fixture_payload(
                    "history/publications/2026/08/publication_123e4567-e89b-42d3-a456-42661417400a.json"
                ),
                "actor_id",
            ),
        ),
        lambda: history.put_history(
            "action",
            _without_json_field(
                _fixture_payload(
                    "history/actions/2026/08/action_123e4567-e89b-42d3-a456-42661417400b.json"
                ),
                "actor_id",
            ),
        ),
        lambda: writes.put_page(
            "content/spaces/studio/notes/page_123e4567-e89b-42d3-a456-426614174005.md",
            _without_markdown_field(
                _fixture_payload(
                    "content/spaces/studio/notes/page_123e4567-e89b-42d3-a456-426614174005.md"
                ),
                "actor_id",
            ),
        ),
        lambda: writes.put_space(
            _without_markdown_field(
                _fixture_payload("content/spaces/studio/_space.md"), "actor_id"
            ),
            replace=False,
        ),
    )

    def persisted(*_args: object, **_kwargs: object) -> WriteState:
        raise AssertionError("invalid Portable bytes reached persistence")

    monkeypatch.setattr(portability_ports, "_immutable_put", persisted)
    for call in calls:
        with pytest.raises(ValueError):
            call()


def test_typed_portable_writes_reject_invalid_nested_family_contracts_before_io(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "brain"
    root.mkdir()
    tenant_id = "tenant_123e4567-e89b-42d3-a456-426614174000"
    source_records, _, _, history, _, _ = local_portability_ports(root, tenant_id)
    cases = (
        (
            "capture",
            "sources/captures/2026/08/capture_123e4567-e89b-42d3-a456-426614174100.json",
        ),
        (
            "proposal",
            "history/proposals/2026/08/proposal_123e4567-e89b-42d3-a456-426614174008.json",
        ),
        (
            "decision",
            "history/decisions/2026/08/decision_123e4567-e89b-42d3-a456-426614174009.json",
        ),
        (
            "publication",
            "history/publications/2026/08/publication_123e4567-e89b-42d3-a456-42661417400a.json",
        ),
        (
            "action",
            "history/actions/2026/08/action_123e4567-e89b-42d3-a456-42661417400b.json",
        ),
        (
            "routing",
            "history/routes/2026/08/route_123e4567-e89b-42d3-a456-426614174012.json",
        ),
    )

    def persisted(*_args: object, **_kwargs: object) -> WriteState:
        raise AssertionError("invalid nested Portable bytes reached persistence")

    monkeypatch.setattr(portability_ports, "_immutable_put", persisted)
    for family, relative in cases:
        value = json.loads(_fixture_payload(relative))
        assert isinstance(value, dict)
        if family == "capture":
            original = value["original_payload"]
            assert isinstance(original, dict)
            original["sha256"] = "0" * 64
        elif family == "proposal":
            evidence = value["evidence"]
            assert isinstance(evidence, list) and evidence
            first = evidence[0]
            assert isinstance(first, dict)
            first["sha256"] = "0" * 64
        elif family == "decision":
            receipt = value["expected_receipt"]
            assert isinstance(receipt, dict)
            receipt["sha256"] = "0" * 64
        elif family == "publication":
            value["published_sha256"] = "0" * 64
        elif family == "action":
            value["action_request_sha256"] = "0" * 64
        else:
            receipt = value["receipt"]
            assert isinstance(receipt, dict)
            receipt["sha256"] = "0" * 64
        payload = portable_canonical_json_bytes(value)

        with pytest.raises(ValueError):
            if family == "capture":
                source_records.put_capture(payload)
            else:
                history.put_history(family, payload)


def test_capture_records_are_immutable_after_initial_persistence(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    root.mkdir()
    tenant_id = "tenant_123e4567-e89b-42d3-a456-426614174000"
    writes = LocalPortableWrites(root=root, tenant_id=tenant_id)
    capture_path = "sources/captures/2026/08/capture_123e4567-e89b-42d3-a456-426614174100.json"
    capture = _fixture_payload(capture_path)
    replacement = json.loads(capture)
    replacement["capture_why"] = "mutable replacement"
    replacement_bytes = portable_canonical_json_bytes(replacement)

    assert writes.put_capture(capture) is WriteState.CREATED
    with pytest.raises(ValueError, match="conflict"):
        writes.replace_capture(replacement_bytes)
    assert (root / capture_path).read_bytes() == capture


def test_portable_ports_reject_root_replacement_before_read_or_write(tmp_path: Path) -> None:
    selected = tmp_path / "selected"
    replacement = tmp_path / "replacement"
    selected.mkdir()
    replacement.mkdir()
    tenant_id = "tenant_123e4567-e89b-42d3-a456-426614174000"
    storage = LocalTenantStorage(root=selected, tenant_id=tenant_id)
    writes = LocalPortableWrites(root=selected, tenant_id=tenant_id)
    displaced = tmp_path / "displaced-selected"
    selected.rename(displaced)
    replacement.rename(selected)

    with pytest.raises(RootConfinementError, match="identity changed"):
        list(storage.portable_files())
    with pytest.raises(RootConfinementError, match="identity changed"):
        writes.put_blob(b"must not reach replacement")

    assert tuple(selected.rglob("*")) == ()
