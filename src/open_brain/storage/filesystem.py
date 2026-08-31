from __future__ import annotations

import base64
import errno
import fcntl
import json
import os
import secrets
import stat
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path, PurePosixPath

from open_brain.core.ids import CaptureId, validate_identifier
from open_brain.core.models import CaptureEnvelope, RawAssetBlob, RawAssetRef, RawCapture
from open_brain.core.ports import PutDisposition, PutResult


class StorageError(Exception):
    """A persistence operation failed without exposing persisted content."""


class RootConfinementError(StorageError):
    """A path did not remain within the approved root capability."""


class DuplicateConflictError(StorageError):
    """An immutable identifier already exists with different bytes."""


class DurabilityError(StorageError):
    """A durable filesystem operation did not complete."""


class StorageUnsupportedPlatformError(StorageError):
    """Required POSIX storage primitives are unavailable."""


class WriteState(StrEnum):
    CREATED = "created"
    ALREADY_EXISTS = "already_exists"


@dataclass(frozen=True, slots=True)
class StoredBlob:
    record_id: str
    relative_path: PurePosixPath
    digest_sha256: str
    state: WriteState


_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
_FILE_READ_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
_FILE_CREATE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)


def _require_platform_support() -> None:
    required = (
        hasattr(os, "O_DIRECTORY"),
        hasattr(os, "O_NOFOLLOW"),
        os.open in os.supports_dir_fd,
        os.mkdir in os.supports_dir_fd,
        os.rename in os.supports_dir_fd,
        os.unlink in os.supports_dir_fd,
        hasattr(fcntl, "flock"),
    )
    if os.name != "posix" or not all(required):
        raise StorageUnsupportedPlatformError("storage platform unsupported")


def _validated_parts(relative: str | PurePosixPath) -> tuple[str, ...]:
    raw = str(relative)
    if (
        not raw
        or raw.startswith("/")
        or "\\" in raw
        or "\x00" in raw
        or any(part in {"", ".", ".."} for part in raw.split("/"))
    ):
        raise RootConfinementError("unsafe relative path")
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts:
        raise RootConfinementError("unsafe relative path")
    return path.parts


def _open_root(root: Path) -> int:
    _require_platform_support()
    if not root.is_absolute():
        raise RootConfinementError("unsafe storage root")
    try:
        metadata = os.lstat(root)
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise RootConfinementError("unsafe storage root")
        return os.open(root, _DIRECTORY_FLAGS)
    except RootConfinementError:
        raise
    except OSError:
        raise RootConfinementError("unsafe storage root") from None


def _open_child_directory(parent_fd: int, name: str, *, create: bool) -> int:
    try:
        if create:
            try:
                os.mkdir(name, mode=0o700, dir_fd=parent_fd)
                os.fsync(parent_fd)
            except FileExistsError:
                pass
        child_fd = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
        if not stat.S_ISDIR(os.fstat(child_fd).st_mode):
            os.close(child_fd)
            raise RootConfinementError("unsafe storage path")
        return child_fd
    except RootConfinementError:
        raise
    except FileNotFoundError:
        if not create:
            raise
        raise DurabilityError("storage directory operation failed") from None
    except OSError as error:
        if error.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise RootConfinementError("unsafe storage path") from None
        raise DurabilityError("storage directory operation failed") from None


def _open_parent(root_fd: int, parts: tuple[str, ...], *, create: bool) -> int:
    current_fd = os.dup(root_fd)
    try:
        for part in parts:
            next_fd = _open_child_directory(current_fd, part, create=create)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except BaseException:
        os.close(current_fd)
        raise


def _read_fd(file_fd: int) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = os.read(file_fd, 64 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _existing_bytes(parent_fd: int, name: str) -> bytes | None:
    try:
        file_fd = os.open(name, _FILE_READ_FLAGS, dir_fd=parent_fd)
    except FileNotFoundError:
        return None
    except OSError as error:
        if error.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise RootConfinementError("unsafe storage target") from None
        raise DurabilityError("storage read failed") from None
    try:
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise RootConfinementError("unsafe storage target")
        return _read_fd(file_fd)
    except OSError:
        raise DurabilityError("storage read failed") from None
    finally:
        os.close(file_fd)


def _write_all(file_fd: int, data: bytes) -> None:
    remaining = memoryview(data)
    while remaining:
        written = os.write(file_fd, remaining)
        if written <= 0:
            raise OSError(errno.EIO, "short write")
        remaining = remaining[written:]


def atomic_write_new(*, root: Path, relative: str | PurePosixPath, data: bytes) -> WriteState:
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    parts = _validated_parts(relative)
    root_fd = _open_root(root)
    lock_fd = -1
    parent_fd = -1
    temp_name: str | None = None
    try:
        try:
            lock_fd = os.open(".write.lock", _FILE_CREATE_FLAGS, 0o600, dir_fd=root_fd)
        except FileExistsError:
            try:
                lock_fd = os.open(".write.lock", os.O_RDWR | os.O_NOFOLLOW, dir_fd=root_fd)
            except OSError:
                raise RootConfinementError("unsafe storage lock") from None
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        parent_fd = _open_parent(root_fd, parts[:-1], create=True)
        existing = _existing_bytes(parent_fd, parts[-1])
        if existing is not None:
            if existing == data:
                return WriteState.ALREADY_EXISTS
            raise DuplicateConflictError("immutable record conflict")

        temp_name = "." + secrets.token_hex(16) + ".tmp"
        file_fd = os.open(temp_name, _FILE_CREATE_FLAGS, 0o600, dir_fd=parent_fd)
        try:
            _write_all(file_fd, data)
            os.fsync(file_fd)
        finally:
            os.close(file_fd)
        os.replace(temp_name, parts[-1], src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        temp_name = None
        os.fsync(parent_fd)
        return WriteState.CREATED
    except (StorageError, TypeError):
        raise
    except OSError:
        raise DurabilityError("durable storage write failed") from None
    finally:
        if temp_name is not None and parent_fd >= 0:
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
                os.fsync(parent_fd)
            except OSError:
                pass
        if parent_fd >= 0:
            os.close(parent_fd)
        if lock_fd >= 0:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(lock_fd)
        os.close(root_fd)


def atomic_replace(
    *,
    root: Path,
    relative: str | PurePosixPath,
    data: bytes,
    require_existing: bool | None = None,
) -> None:
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    parts = _validated_parts(relative)
    root_fd = _open_root(root)
    lock_fd = -1
    parent_fd = -1
    temp_name: str | None = None
    try:
        try:
            lock_fd = os.open(".write.lock", _FILE_CREATE_FLAGS, 0o600, dir_fd=root_fd)
        except FileExistsError:
            try:
                lock_fd = os.open(".write.lock", os.O_RDWR | os.O_NOFOLLOW, dir_fd=root_fd)
            except OSError:
                raise RootConfinementError("unsafe storage lock") from None
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        parent_fd = _open_parent(root_fd, parts[:-1], create=True)
        existing = _existing_bytes(parent_fd, parts[-1])
        if require_existing is True and existing is None:
            raise StorageError("replace target missing")
        if require_existing is False and existing is not None:
            raise DuplicateConflictError("replace target already exists")

        temp_name = "." + secrets.token_hex(16) + ".tmp"
        file_fd = os.open(temp_name, _FILE_CREATE_FLAGS, 0o600, dir_fd=parent_fd)
        try:
            _write_all(file_fd, data)
            os.fsync(file_fd)
        finally:
            os.close(file_fd)
        os.replace(temp_name, parts[-1], src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        temp_name = None
        os.fsync(parent_fd)
    except (StorageError, TypeError):
        raise
    except OSError:
        raise DurabilityError("durable storage write failed") from None
    finally:
        if temp_name is not None and parent_fd >= 0:
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
                os.fsync(parent_fd)
            except OSError:
                pass
        if parent_fd >= 0:
            os.close(parent_fd)
        if lock_fd >= 0:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(lock_fd)
        os.close(root_fd)


def read_confined(*, root: Path, relative: str | PurePosixPath) -> bytes | None:
    parts = _validated_parts(relative)
    root_fd = _open_root(root)
    parent_fd = -1
    try:
        try:
            parent_fd = _open_parent(root_fd, parts[:-1], create=False)
        except FileNotFoundError:
            return None
        return _existing_bytes(parent_fd, parts[-1])
    finally:
        if parent_fd >= 0:
            os.close(parent_fd)
        os.close(root_fd)


def resolve_generated_path(root: Path, relative: str | PurePosixPath) -> Path:
    parts = _validated_parts(relative)
    root_fd = _open_root(root)
    try:
        current_fd = os.dup(root_fd)
        try:
            for part in parts[:-1]:
                next_fd = _open_child_directory(current_fd, part, create=False)
                os.close(current_fd)
                current_fd = next_fd
            try:
                final_fd = os.open(parts[-1], _FILE_READ_FLAGS, dir_fd=current_fd)
            except FileNotFoundError:
                pass
            except OSError as error:
                if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                    raise RootConfinementError("unsafe storage target") from None
                raise DurabilityError("storage target operation failed") from None
            else:
                try:
                    if not stat.S_ISREG(os.fstat(final_fd).st_mode):
                        raise RootConfinementError("unsafe storage target")
                finally:
                    os.close(final_fd)
        finally:
            os.close(current_fd)
    finally:
        os.close(root_fd)
    return root.joinpath(*parts)


def raw_relative_path(capture_id: CaptureId | str) -> PurePosixPath:
    try:
        value = validate_identifier(str(capture_id), prefix="cap_")
    except ValueError:
        raise RootConfinementError("invalid capture identifier") from None
    return PurePosixPath("raw", value[4:6], value + ".json")


def _raw_capture_bytes(capture: RawCapture) -> bytes:
    value = {
        "assets": [
            {
                "data_base64": base64.b64encode(asset.data).decode("ascii"),
                "ref": asset.ref.to_dict(),
            }
            for asset in capture.assets
        ],
        "envelope": capture.envelope.to_dict(),
    }
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _raw_capture_from_bytes(payload: bytes) -> RawCapture:
    try:
        value = json.loads(payload.decode("utf-8"))
        if not isinstance(value, dict) or set(value) != {"assets", "envelope"}:
            raise ValueError
        envelope_value = value["envelope"]
        assets_value = value["assets"]
        if not isinstance(envelope_value, dict) or not isinstance(assets_value, list):
            raise ValueError
        envelope = CaptureEnvelope.from_dict(envelope_value)
        assets: list[RawAssetBlob] = []
        for item in assets_value:
            if not isinstance(item, dict) or set(item) != {"data_base64", "ref"}:
                raise ValueError
            ref_value = item["ref"]
            encoded = item["data_base64"]
            if not isinstance(ref_value, dict) or not isinstance(encoded, str):
                raise ValueError
            ref = RawAssetRef.from_dict(ref_value)
            data = base64.b64decode(encoded, validate=True)
            assets.append(RawAssetBlob.create(ref=ref, data=data))
        result = RawCapture.create(envelope=envelope, assets=tuple(assets))
        if _raw_capture_bytes(result) != payload:
            raise ValueError
        return result
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        raise StorageError("invalid stored raw capture") from None


class AtomicFilesystemRawStore:
    def __init__(self, *, root: Path) -> None:
        root_fd = _open_root(root)
        os.close(root_fd)
        self._root = root

    def put_if_absent(self, capture: RawCapture) -> PutResult:
        if not isinstance(capture, RawCapture):
            raise StorageError("invalid raw capture")
        canonical_capture = _raw_capture_from_bytes(_raw_capture_bytes(capture))
        payload = _raw_capture_bytes(canonical_capture)
        capture_id = canonical_capture.envelope.capture_id
        state = atomic_write_new(
            root=self._root,
            relative=raw_relative_path(capture_id),
            data=payload,
        )
        return PutResult(
            disposition=(
                PutDisposition.CREATED if state is WriteState.CREATED else PutDisposition.DUPLICATE
            ),
            record_id=str(capture_id),
            digest_sha256=sha256(payload).hexdigest(),
        )

    def get(self, capture_id: CaptureId) -> RawCapture | None:
        payload = read_confined(root=self._root, relative=raw_relative_path(capture_id))
        if payload is None:
            return None
        capture = _raw_capture_from_bytes(payload)
        if capture.envelope.capture_id != capture_id:
            raise StorageError("stored raw capture identity mismatch")
        return capture
