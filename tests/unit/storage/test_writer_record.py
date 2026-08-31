from __future__ import annotations

import os
import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest

from open_brain.storage.filesystem import DurabilityError, atomic_replace
from open_brain.storage.writer_record import (
    CanonicalWriterRecord,
    WriterRecordError,
    read_canonical_writer_record,
    write_canonical_writer_record,
)

_RECORDED_AT = datetime(2026, 8, 16, 20, 0, tzinfo=UTC)
_RELATIVE_PATH = ".open-brain-host/writer-record.json"


def test_canonical_writer_record_round_trips_with_a_verified_digest() -> None:
    record = CanonicalWriterRecord.create(
        identity_id="mac-mini",
        generation=1,
        recorded_at=_RECORDED_AT,
    )

    payload = record.to_bytes()

    assert record.digest_sha256 == (
        "b3d31e8840265192e685ba5366936d11a344d77834f3c605fe080dfa1a821368"
    )
    assert CanonicalWriterRecord.from_bytes(payload) == record
    assert b'"identity_id":"mac-mini"' in payload
    assert b'"recorded_at":"2026-08-16T20:00:00Z"' in payload


def test_canonical_writer_record_rejects_tampering_and_unknown_fields() -> None:
    record = CanonicalWriterRecord.create(
        identity_id="mac-mini",
        generation=1,
        recorded_at=_RECORDED_AT,
    )
    tampered = record.to_bytes().replace(b'"generation":1', b'"generation":2')
    extended = record.to_bytes()[:-1] + b',"unexpected":true}'

    with pytest.raises(WriterRecordError, match="invalid canonical writer record"):
        CanonicalWriterRecord.from_bytes(tampered)
    with pytest.raises(WriterRecordError, match="invalid canonical writer record"):
        CanonicalWriterRecord.from_bytes(extended)


def test_writer_record_read_returns_none_when_absent(tmp_path: Path) -> None:
    assert read_canonical_writer_record(tmp_path) is None


def test_writer_record_write_is_private_monotonic_and_read_back_verified(
    tmp_path: Path,
) -> None:
    first = write_canonical_writer_record(
        state_root=tmp_path,
        identity_id="mac-mini",
        generation=1,
        recorded_at=_RECORDED_AT,
    )
    second = write_canonical_writer_record(
        state_root=tmp_path,
        identity_id="mac-mini",
        generation=2,
        recorded_at=datetime(2026, 8, 16, 20, 5, tzinfo=UTC),
    )

    path = tmp_path / _RELATIVE_PATH
    assert first.generation == 1
    assert second.generation == 2
    assert read_canonical_writer_record(tmp_path) == second
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


@pytest.mark.parametrize("generation", [0, 1])
def test_writer_record_rejects_nonincreasing_generation(
    generation: int,
    tmp_path: Path,
) -> None:
    write_canonical_writer_record(
        state_root=tmp_path,
        identity_id="mac-mini",
        generation=1,
        recorded_at=_RECORDED_AT,
    )

    with pytest.raises(WriterRecordError, match="generation must increase"):
        write_canonical_writer_record(
            state_root=tmp_path,
            identity_id="mac-mini",
            generation=generation,
            recorded_at=_RECORDED_AT,
        )


def test_writer_record_rejects_independent_read_back_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import open_brain.storage.writer_record as writer_record_module

    readings = iter((None, None))
    monkeypatch.setattr(
        writer_record_module,
        "read_canonical_writer_record",
        lambda _: next(readings),
    )

    with pytest.raises(WriterRecordError, match="read-back mismatch"):
        write_canonical_writer_record(
            state_root=tmp_path,
            identity_id="mac-mini",
            generation=1,
            recorded_at=_RECORDED_AT,
        )


def test_writer_record_failed_replace_preserves_the_previous_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = write_canonical_writer_record(
        state_root=tmp_path,
        identity_id="mac-mini",
        generation=1,
        recorded_at=_RECORDED_AT,
    )

    def fail_publish(*args: object, **kwargs: object) -> None:
        raise OSError("synthetic publish failure")

    monkeypatch.setattr(os, "replace", fail_publish)
    with pytest.raises(DurabilityError):
        write_canonical_writer_record(
            state_root=tmp_path,
            identity_id="mac-mini",
            generation=2,
            recorded_at=datetime(2026, 8, 16, 20, 5, tzinfo=UTC),
        )

    monkeypatch.undo()
    assert read_canonical_writer_record(tmp_path) == first


def test_writer_record_reader_rejects_noncanonical_stored_bytes(tmp_path: Path) -> None:
    atomic_replace(root=tmp_path, relative=_RELATIVE_PATH, data=b"{}")

    with pytest.raises(WriterRecordError, match="invalid canonical writer record"):
        read_canonical_writer_record(tmp_path)
