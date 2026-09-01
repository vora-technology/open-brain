from __future__ import annotations

import errno
import json
import os
import re
import socket
import stat
import threading
import uuid
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from open_brain.engine import (
    DaemonAuthorityCapability,
    LocalEngineContext,
    TextPayload,
    acquire_daemon_authority,
    canonical_json_bytes,
    require_daemon_authority,
)
from open_brain.profile import open_existing_single_user_local

from .appliance_application import ApplianceApplication

CONTROL_SCHEMA_VERSION: Final[int] = 1
CONTROL_ACTION_CAPTURE_TEXT: Final[str] = "capture.accept.text"
CONTROL_STATUS_ACCEPTED: Final[str] = "accepted"
MAXIMUM_CONTROL_ENVELOPE_BYTES: Final[int] = 4_096
RUN_DIRECTORY_MODE: Final[int] = 0o700
SOCKET_MODE: Final[int] = 0o600
CONTROL_CONNECTION_TIMEOUT_SECONDS: Final[float] = 1.0
_DELIVERY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")


class ApplianceControlProtocolError(RuntimeError):
    """The appliance control envelope is invalid or out of bounds."""


class ApplianceControlSocketError(RuntimeError):
    """The appliance control socket path is unsafe or unusable."""


class ApplianceControlUnavailableError(RuntimeError):
    """The appliance control socket is unavailable."""


class ApplianceDaemonConflictError(RuntimeError):
    """Another appliance daemon already owns the root authority."""


@dataclass(frozen=True, slots=True)
class ControlRequest:
    delivery_id: str
    text: str
    action: str = CONTROL_ACTION_CAPTURE_TEXT
    schema_version: int = CONTROL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _validate_control_action(self.action)
        if self.schema_version != CONTROL_SCHEMA_VERSION:
            raise ApplianceControlProtocolError("unsupported request envelope")
        _validate_delivery_id(self.delivery_id, envelope="request")
        if not isinstance(self.text, str) or not self.text:
            raise ApplianceControlProtocolError("invalid request envelope")
        _validate_control_size(self.to_dict(), envelope="request")

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "delivery_id": self.delivery_id,
            "schema_version": self.schema_version,
            "text": self.text,
        }

    def to_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_bytes(cls, payload: bytes) -> ControlRequest:
        value = _parse_control_bytes(payload, envelope="request")
        expected = {"action", "delivery_id", "schema_version", "text"}
        if set(value) != expected:
            raise ApplianceControlProtocolError("invalid request envelope")
        return cls(
            action=_required_str(value, "action", envelope="request"),
            delivery_id=_required_str(value, "delivery_id", envelope="request"),
            schema_version=_required_int(value, "schema_version", envelope="request"),
            text=_required_str(value, "text", envelope="request"),
        )


@dataclass(frozen=True, slots=True)
class ControlReceipt:
    delivery_id: str
    capture_id: str
    state: str
    action: str = CONTROL_ACTION_CAPTURE_TEXT
    status: str = CONTROL_STATUS_ACCEPTED
    schema_version: int = CONTROL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _validate_control_action(self.action)
        if self.status != CONTROL_STATUS_ACCEPTED or self.schema_version != CONTROL_SCHEMA_VERSION:
            raise ApplianceControlProtocolError("unsupported receipt envelope")
        _validate_delivery_id(self.delivery_id, envelope="receipt")
        _validate_portable_identifier(self.capture_id, prefix="capture")
        if self.state != "inbox":
            raise ApplianceControlProtocolError("invalid receipt envelope")
        _validate_control_size(self.to_dict(), envelope="receipt")

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "capture_id": self.capture_id,
            "delivery_id": self.delivery_id,
            "schema_version": self.schema_version,
            "state": self.state,
            "status": self.status,
        }

    def to_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_bytes(cls, payload: bytes) -> ControlReceipt:
        value = _parse_control_bytes(payload, envelope="receipt")
        expected = {
            "action",
            "capture_id",
            "delivery_id",
            "schema_version",
            "state",
            "status",
        }
        if set(value) != expected:
            raise ApplianceControlProtocolError("invalid receipt envelope")
        return cls(
            action=_required_str(value, "action", envelope="receipt"),
            capture_id=_required_str(value, "capture_id", envelope="receipt"),
            delivery_id=_required_str(value, "delivery_id", envelope="receipt"),
            schema_version=_required_int(value, "schema_version", envelope="receipt"),
            state=_required_str(value, "state", envelope="receipt"),
            status=_required_str(value, "status", envelope="receipt"),
        )


class ApplianceDaemon:
    """Own one root authority, one confined control socket, and one mutation path."""

    def __init__(
        self,
        root: Path,
        *,
        application_factory: (
            Callable[[Path, DaemonAuthorityCapability], ApplianceApplication] | None
        ) = None,
        connection_timeout: float = CONTROL_CONNECTION_TIMEOUT_SECONDS,
    ) -> None:
        if not isinstance(root, Path):
            raise ValueError("invalid appliance root")
        _validate_timeout(connection_timeout)
        self._root = root
        self._application_factory = application_factory or _open_mutating_application
        self._connection_timeout = connection_timeout
        self._profile: LocalEngineContext | None = None
        self._authority: DaemonAuthorityCapability | None = None
        self._application: ApplianceApplication | None = None
        self._listener: socket.socket | None = None
        self._exit_stack: ExitStack | None = None
        self._stop_event = threading.Event()

    def __enter__(self) -> ApplianceDaemon:
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.stop()

    @property
    def socket_path(self) -> Path:
        return _control_socket_path(self._root)

    def start(self) -> None:
        if self._exit_stack is not None:
            raise RuntimeError("appliance daemon already started")
        profile = open_existing_single_user_local(self._root)
        stack = ExitStack()
        authority: DaemonAuthorityCapability
        try:
            try:
                authority = stack.enter_context(acquire_control_socket_authority(profile))
            except Exception as error:
                if type(error).__name__ != "LockBusyError":
                    raise
                raise ApplianceDaemonConflictError("appliance daemon already active") from error
            application = self._application_factory(self._root, authority)
            _ensure_run_directory(_run_directory(self._root))
            cleanup_stale_control_socket(profile, authority)
            listener = _bind_listener(self.socket_path)
        except Exception:
            stack.close()
            raise
        self._profile = profile
        self._authority = authority
        self._application = application
        self._listener = listener
        self._exit_stack = stack
        self._stop_event.clear()

    def serve_once(self, *, timeout: float = 0.1) -> bool:
        listener = self._listener
        if listener is None or self._application is None:
            raise RuntimeError("appliance daemon is not running")
        listener.settimeout(timeout)
        try:
            connection, _ = listener.accept()
        except TimeoutError:
            return False
        except OSError:
            if self._stop_event.is_set():
                return False
            raise
        with connection:
            connection.settimeout(self._connection_timeout)
            request = ControlRequest.from_bytes(_read_bounded_bytes(connection))
            assert self._application.mutations is not None
            accepted = self._application.mutations.capture.accept(
                TextPayload(request.text),
                delivery_id=request.delivery_id,
            )
            _send_control_bytes(
                connection,
                ControlReceipt(
                    delivery_id=request.delivery_id,
                    capture_id=accepted.capture_id,
                    state=accepted.state,
                ).to_bytes(),
            )
        return True

    def serve_until_stopped(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.serve_once()
            except (ApplianceControlProtocolError, ConnectionError, TimeoutError):
                continue

    def stop(self) -> None:
        listener = self._listener
        profile = self._profile
        authority = self._authority
        stack = self._exit_stack
        if listener is None or profile is None or authority is None or stack is None:
            return
        self._stop_event.set()
        try:
            listener.close()
        finally:
            self._listener = None
        try:
            cleanup_stale_control_socket(profile, authority)
        finally:
            stack.close()
            self._exit_stack = None
            self._profile = None
            self._authority = None
            self._application = None


def cleanup_stale_control_socket(
    profile: LocalEngineContext,
    authority: object | None,
) -> None:
    if not isinstance(profile, LocalEngineContext):
        raise ValueError("invalid local profile")
    require_daemon_authority(profile, authority)
    path = _control_socket_path(profile.root)
    try:
        metadata = _lstat_path(path)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(metadata.st_mode):
        raise ApplianceControlSocketError("control socket symlink replacement refused")
    if not stat.S_ISSOCK(metadata.st_mode):
        raise ApplianceControlSocketError("control socket non-socket replacement refused")
    if not _same_identity(metadata, _lstat_path(path)):
        raise ApplianceControlSocketError("control socket replaced during cleanup")
    path.unlink()


@contextmanager
def acquire_control_socket_authority(
    profile: LocalEngineContext,
) -> Iterator[DaemonAuthorityCapability]:
    if not isinstance(profile, LocalEngineContext):
        raise ValueError("invalid local profile")
    with acquire_daemon_authority(profile) as authority:
        yield authority


def request_control(
    root: Path,
    request: ControlRequest,
    *,
    timeout: float = 1.0,
) -> ControlReceipt:
    if not isinstance(root, Path):
        raise ValueError("invalid appliance root")
    _validate_timeout(timeout)
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(timeout)
    try:
        try:
            client.connect(str(_control_socket_path(root)))
        except OSError as error:
            raise ApplianceControlUnavailableError(
                "appliance control socket unavailable"
            ) from error
        client.sendall(request.to_bytes())
        client.shutdown(socket.SHUT_WR)
        return ControlReceipt.from_bytes(_read_bounded_bytes(client))
    finally:
        client.close()


def _open_mutating_application(
    root: Path,
    authority: DaemonAuthorityCapability,
) -> ApplianceApplication:
    return ApplianceApplication.open_mutating(root, authority=authority)


def _run_directory(root: Path) -> Path:
    return root / ".open-brain" / "run"


def _control_socket_path(root: Path) -> Path:
    return _run_directory(root) / "control.sock"


def _ensure_run_directory(path: Path) -> None:
    try:
        metadata = _lstat_path(path)
    except FileNotFoundError:
        path.mkdir(exist_ok=True)
        os.chmod(path, RUN_DIRECTORY_MODE)
        return
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ApplianceControlSocketError("invalid appliance run directory")
    os.chmod(path, RUN_DIRECTORY_MODE)


def _bind_listener(path: Path) -> socket.socket:
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        listener.bind(str(path))
        listener.listen()
        os.chmod(path, SOCKET_MODE)
        return listener
    except OSError as error:
        listener.close()
        if error.errno == errno.EADDRINUSE:
            raise ApplianceControlSocketError("control socket already bound") from error
        raise


def _read_bounded_bytes(connection: socket.socket) -> bytes:
    chunks = bytearray()
    limit = MAXIMUM_CONTROL_ENVELOPE_BYTES + 1
    while len(chunks) <= MAXIMUM_CONTROL_ENVELOPE_BYTES:
        chunk = connection.recv(limit - len(chunks))
        if not chunk:
            break
        chunks.extend(chunk)
    payload = bytes(chunks)
    if len(payload) > MAXIMUM_CONTROL_ENVELOPE_BYTES:
        raise ApplianceControlProtocolError("control envelope is too large")
    return payload


def _parse_control_bytes(payload: bytes, *, envelope: str) -> dict[str, object]:
    if not isinstance(payload, bytes):
        raise ApplianceControlProtocolError(f"invalid {envelope} envelope")
    if len(payload) > MAXIMUM_CONTROL_ENVELOPE_BYTES:
        raise ApplianceControlProtocolError("control envelope is too large")
    try:
        value = json.loads(payload.decode("utf-8"))
        canonical = canonical_json_bytes(value)
    except Exception as error:
        raise ApplianceControlProtocolError(f"invalid {envelope} envelope") from error
    if not isinstance(value, dict):
        raise ApplianceControlProtocolError(f"invalid {envelope} envelope")
    if canonical != payload:
        raise ApplianceControlProtocolError(f"{envelope} envelope must be canonical")
    return value


def _required_int(value: dict[str, object], key: str, *, envelope: str) -> int:
    item = value.get(key)
    if not isinstance(item, int) or isinstance(item, bool):
        raise ApplianceControlProtocolError(f"invalid {envelope} envelope")
    return item


def _required_str(value: dict[str, object], key: str, *, envelope: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise ApplianceControlProtocolError(f"invalid {envelope} envelope")
    return item


def _validate_control_action(value: str) -> None:
    if value != CONTROL_ACTION_CAPTURE_TEXT:
        raise ApplianceControlProtocolError("unsupported action")


def _validate_delivery_id(value: str, *, envelope: str) -> None:
    if not isinstance(value, str) or _DELIVERY_ID.fullmatch(value) is None:
        raise ApplianceControlProtocolError(f"invalid {envelope} envelope")


def _validate_timeout(value: float) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
        raise ValueError("invalid appliance control timeout")


def _validate_control_size(value: object, *, envelope: str) -> None:
    if len(canonical_json_bytes(value)) > MAXIMUM_CONTROL_ENVELOPE_BYTES:
        raise ApplianceControlProtocolError(f"{envelope} envelope is too large")


def _validate_portable_identifier(value: str, *, prefix: str) -> None:
    marker = prefix + "_"
    if not isinstance(value, str) or not value.startswith(marker):
        raise ApplianceControlProtocolError("invalid receipt envelope")
    try:
        identifier = uuid.UUID(value.removeprefix(marker))
    except ValueError as error:
        raise ApplianceControlProtocolError("invalid receipt envelope") from error
    if identifier.version != 4 or value != f"{prefix}_{identifier}":
        raise ApplianceControlProtocolError("invalid receipt envelope")


def _same_identity(first: os.stat_result, second: os.stat_result) -> bool:
    return (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)


def _send_control_bytes(connection: socket.socket, payload: bytes) -> None:
    connection.sendall(payload)


def _lstat_path(path: Path) -> os.stat_result:
    return path.lstat()


__all__ = [
    "MAXIMUM_CONTROL_ENVELOPE_BYTES",
    "ApplianceControlProtocolError",
    "ApplianceControlSocketError",
    "ApplianceControlUnavailableError",
    "ApplianceDaemon",
    "ApplianceDaemonConflictError",
    "CONTROL_ACTION_CAPTURE_TEXT",
    "ControlRequest",
    "ControlReceipt",
    "acquire_control_socket_authority",
    "cleanup_stale_control_socket",
    "request_control",
]
