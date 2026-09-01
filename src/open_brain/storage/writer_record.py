from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal

from open_brain.core.ids import canonical_json_bytes
from open_brain.core.locks import LockScope

from .filesystem import StorageError, atomic_replace, read_confined
from .locks import FileLease


class WriterRecordError(StorageError):
    """Canonical-writer metadata is absent, malformed, or non-monotonic."""


_IDENTITY = re.compile(r"[a-z][a-z0-9-]{0,63}")
_DIGEST = re.compile(r"[0-9a-f]{64}")
_RELATIVE_PATH = ".open-brain-host/writer-record.json"
_FIELDS = frozenset({"version", "identity_id", "generation", "recorded_at", "digest_sha256"})
_MAX_RECORD_BYTES = 2048


@dataclass(frozen=True, slots=True)
class CanonicalWriterRecord:
    """Digest-bound designation of the current canonical writer identity."""

    version: Literal[1]
    identity_id: str
    generation: int
    recorded_at: datetime
    digest_sha256: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.recorded_at, datetime)
            or self.recorded_at.tzinfo is None
            or self.recorded_at.utcoffset() is None
        ):
            raise WriterRecordError("invalid canonical writer record")
        object.__setattr__(self, "recorded_at", self.recorded_at.astimezone(UTC))
        self._validate()

    @classmethod
    def create(
        cls,
        *,
        identity_id: str,
        generation: int,
        recorded_at: datetime,
    ) -> CanonicalWriterRecord:
        normalized = _utc(recorded_at)
        body = _body(
            identity_id=identity_id,
            generation=generation,
            recorded_at=normalized,
        )
        return cls(
            version=1,
            identity_id=identity_id,
            generation=generation,
            recorded_at=normalized,
            digest_sha256=sha256(canonical_json_bytes(body)).hexdigest(),
        )

    def _validate(self) -> None:
        expected_digest = sha256(canonical_json_bytes(self._body())).hexdigest()
        if (
            type(self.version) is not int
            or self.version != 1
            or not isinstance(self.identity_id, str)
            or _IDENTITY.fullmatch(self.identity_id) is None
            or type(self.generation) is not int
            or self.generation < 1
            or not isinstance(self.recorded_at, datetime)
            or self.recorded_at.tzinfo is not UTC
            or not isinstance(self.digest_sha256, str)
            or _DIGEST.fullmatch(self.digest_sha256) is None
            or self.digest_sha256 != expected_digest
        ):
            raise WriterRecordError("invalid canonical writer record")

    def _body(self) -> dict[str, object]:
        return _body(
            identity_id=self.identity_id,
            generation=self.generation,
            recorded_at=self.recorded_at,
        )

    def to_dict(self) -> dict[str, object]:
        self._validate()
        return {**self._body(), "digest_sha256": self.digest_sha256}

    def to_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_bytes(cls, payload: bytes) -> CanonicalWriterRecord:
        if type(payload) is not bytes or not payload or len(payload) > _MAX_RECORD_BYTES:
            raise WriterRecordError("invalid canonical writer record")
        try:
            value = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object)
            if type(value) is not dict or frozenset(value) != _FIELDS:
                raise WriterRecordError("invalid canonical writer record")
            recorded_at = value["recorded_at"]
            if not isinstance(recorded_at, str) or not recorded_at.endswith("Z"):
                raise WriterRecordError("invalid canonical writer record")
            record = cls(
                version=1 if value["version"] == 1 else value["version"],
                identity_id=value["identity_id"],
                generation=value["generation"],
                recorded_at=datetime.fromisoformat(recorded_at[:-1] + "+00:00"),
                digest_sha256=value["digest_sha256"],
            )
        except WriterRecordError:
            raise
        except (KeyError, TypeError, ValueError, UnicodeError, json.JSONDecodeError):
            raise WriterRecordError("invalid canonical writer record") from None
        if record.to_bytes() != payload:
            raise WriterRecordError("invalid canonical writer record")
        return record


def read_canonical_writer_record(state_root: Path) -> CanonicalWriterRecord | None:
    payload = read_confined(root=state_root, relative=_RELATIVE_PATH)
    if payload is None:
        return None
    return CanonicalWriterRecord.from_bytes(payload)


def write_canonical_writer_record(
    *,
    state_root: Path,
    identity_id: str,
    generation: int,
    recorded_at: datetime,
) -> CanonicalWriterRecord:
    if type(generation) is not int or generation < 1:
        raise WriterRecordError("canonical writer generation must increase")
    record = CanonicalWriterRecord.create(
        identity_id=identity_id,
        generation=generation,
        recorded_at=recorded_at,
    )
    authority_lease = FileLease(
        state_root,
        identity_id,
        clock=lambda: record.recorded_at,
    )
    with authority_lease.acquire(LockScope.SHARED_WRITER):
        current = read_canonical_writer_record(state_root)
        if current is not None and generation <= current.generation:
            raise WriterRecordError("canonical writer generation must increase")
        atomic_replace(
            root=state_root,
            relative=_RELATIVE_PATH,
            data=record.to_bytes(),
            require_existing=current is not None,
        )
        read_back = read_canonical_writer_record(state_root)
        if read_back != record:
            raise WriterRecordError("canonical writer read-back mismatch")
    return record


def _body(*, identity_id: str, generation: int, recorded_at: datetime) -> dict[str, object]:
    return {
        "version": 1,
        "identity_id": identity_id,
        "generation": generation,
        "recorded_at": _timestamp(recorded_at),
    }


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise WriterRecordError("invalid canonical writer record")
    return value.astimezone(UTC)


def _timestamp(value: datetime) -> str:
    timespec = "microseconds" if value.microsecond else "seconds"
    return value.isoformat(timespec=timespec).replace("+00:00", "Z")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise WriterRecordError("invalid canonical writer record")
        value[key] = item
    return value
