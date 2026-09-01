"""Same-filesystem sibling staging for Portable Brain promotion."""

from __future__ import annotations

import ctypes
import errno
import os
import stat
import sys
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from .filesystem import RootIdentity


class StagingError(RuntimeError):
    """A staged Portable root cannot be safely created or promoted."""


_DIRECTORY_FLAGS = (
    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
)


def _rename_noreplace(parent_fd: int, source: str, destination: str) -> None:
    """Atomically create ``destination`` from ``source`` without replacing a name."""
    if os.name != "posix":
        raise StagingError("atomic no-replace promotion is unsupported")
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        rename = getattr(libc, "renameatx_np", None)
        if rename is None:
            raise StagingError("atomic no-replace promotion is unsupported")
        rename.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename.restype = ctypes.c_int
        result = rename(parent_fd, source.encode(), parent_fd, destination.encode(), 0x00000004)
    elif sys.platform.startswith("linux"):
        rename = getattr(libc, "renameat2", None)
        if rename is None:
            raise StagingError("atomic no-replace promotion is unsupported")
        rename.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename.restype = ctypes.c_int
        result = rename(parent_fd, source.encode(), parent_fd, destination.encode(), 0x00000001)
    else:
        raise StagingError("atomic no-replace promotion is unsupported")
    if result == 0:
        return
    error = ctypes.get_errno()
    if error in {errno.EEXIST, errno.ENOTEMPTY}:
        raise StagingError("portability destination already exists")
    raise OSError(error, "atomic no-replace promotion failed")


def _parts(relative: str) -> tuple[str, ...]:
    path = PurePosixPath(relative)
    if (
        not relative
        or path.is_absolute()
        or "\\" in relative
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise StagingError("unsafe staged path")
    return path.parts


def _open_directory(parent_fd: int, name: str, *, create: bool) -> tuple[int, bool]:
    created = False
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except FileNotFoundError:
        if not create:
            raise
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
            created = True
        except FileExistsError:
            pass
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) & 0o077:
        os.close(descriptor)
        raise StagingError("unsafe staged directory")
    return descriptor, created


def _open_absolute_directory(
    path: Path, expected_identity: RootIdentity | None = None
) -> int:
    if not isinstance(path, Path) or not path.is_absolute():
        raise StagingError("unsafe portability directory")
    parts = path.parts
    if not parts or any(part in {"", ".", ".."} for part in parts[1:]):
        raise StagingError("unsafe portability directory")
    current_fd = -1
    try:
        current_fd = os.open(parts[0], _DIRECTORY_FLAGS)
        for part in parts[1:]:
            child_fd = os.open(part, _DIRECTORY_FLAGS, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = child_fd
        metadata = os.fstat(current_fd)
    except OSError as error:
        if current_fd >= 0:
            os.close(current_fd)
        raise StagingError("unsafe portability directory") from error
    if expected_identity is not None and _identity(metadata) != expected_identity:
        os.close(current_fd)
        raise StagingError("portability directory identity changed")
    return current_fd


def _descriptor_descends_from(directory_fd: int, ancestor_identity: RootIdentity) -> bool:
    current_fd = os.dup(directory_fd)
    try:
        while True:
            current = _identity(os.fstat(current_fd))
            if current == ancestor_identity:
                return True
            parent_fd = os.open("..", _DIRECTORY_FLAGS, dir_fd=current_fd)
            try:
                parent = _identity(os.fstat(parent_fd))
            except OSError:
                os.close(parent_fd)
                raise
            if parent == current:
                os.close(parent_fd)
                return False
            os.close(current_fd)
            current_fd = parent_fd
    finally:
        os.close(current_fd)


def capture_destination_parent(
    destination: Path,
    *,
    forbidden_ancestor_identity: RootIdentity,
    expected_identity: RootIdentity | None = None,
) -> RootIdentity:
    """Pin a no-follow parent and reject a parent inside the source capability."""
    parent_fd = _open_absolute_directory(destination.parent, expected_identity)
    try:
        metadata = os.fstat(parent_fd)
        if stat.S_IMODE(metadata.st_mode) != 0o700:
            raise StagingError("unsafe portability destination parent")
        if _descriptor_descends_from(parent_fd, forbidden_ancestor_identity):
            raise StagingError("portability destination is inside its source")
        return _identity(metadata)
    finally:
        os.close(parent_fd)


def destination_child_identity(
    destination: Path,
    *,
    parent_identity: RootIdentity,
) -> RootIdentity | None:
    parent_fd = _open_absolute_directory(destination.parent, parent_identity)
    try:
        try:
            metadata = os.stat(
                destination.name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return None
        if not stat.S_ISDIR(metadata.st_mode):
            raise StagingError("unsafe portability destination")
        try:
            child_fd = os.open(
                destination.name,
                _DIRECTORY_FLAGS,
                dir_fd=parent_fd,
            )
        except OSError as error:
            raise StagingError("unsafe portability destination") from error
        try:
            if _identity(os.fstat(child_fd)) != _identity(metadata):
                raise StagingError("portability destination identity changed")
            return _identity(metadata)
        finally:
            os.close(child_fd)
    finally:
        os.close(parent_fd)


def remove_empty_destination(
    destination: Path,
    *,
    parent_identity: RootIdentity,
    child_identity: RootIdentity,
) -> None:
    """Remove one pinned private empty directory before no-replace promotion."""

    parent_fd = _open_absolute_directory(destination.parent, parent_identity)
    child_fd = -1
    try:
        observed = os.stat(destination.name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISDIR(observed.st_mode) or _identity(observed) != child_identity:
            raise StagingError("disposable destination identity changed")
        child_fd = os.open(destination.name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
        current = os.fstat(child_fd)
        with os.scandir(child_fd) as entries:
            destination_is_empty = next(entries, None) is None
        if (
            _identity(current) != child_identity
            or stat.S_IMODE(current.st_mode) != 0o700
            or not destination_is_empty
        ):
            raise StagingError("disposable destination must be empty and private")
        os.close(child_fd)
        child_fd = -1
        observed = os.stat(destination.name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISDIR(observed.st_mode) or _identity(observed) != child_identity:
            raise StagingError("disposable destination identity changed")
        os.rmdir(destination.name, dir_fd=parent_fd)
        os.fsync(parent_fd)
    except StagingError:
        raise
    except OSError as error:
        raise StagingError("disposable destination cannot be removed safely") from error
    finally:
        if child_fd >= 0:
            os.close(child_fd)
        os.close(parent_fd)


def _write_all(descriptor: int, payload: bytes) -> None:
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("short staged write")
        remaining = remaining[written:]


def _identity(metadata: os.stat_result) -> tuple[int, int]:
    return (metadata.st_dev, metadata.st_ino)


def _open_regular(parent_fd: int, name: str, expected: os.stat_result) -> int:
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except OSError as error:
        raise StagingError("unsafe staged file") from error
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or _identity(metadata) != _identity(expected)
    ):
        os.close(descriptor)
        raise StagingError("unsafe staged file")
    return descriptor


def _fsync_tree_descriptor(directory_fd: int) -> None:
    try:
        entries = sorted(os.scandir(directory_fd), key=lambda entry: entry.name)
    except OSError as error:
        raise StagingError("staging directory cannot be synced") from error
    for entry in entries:
        try:
            metadata = entry.stat(follow_symlinks=False)
        except OSError as error:
            raise StagingError("staging directory cannot be synced") from error
        if stat.S_ISDIR(metadata.st_mode):
            child_fd, _ = _open_directory(directory_fd, entry.name, create=False)
            try:
                if _identity(os.fstat(child_fd)) != _identity(metadata):
                    raise StagingError("staged directory identity changed")
                _fsync_tree_descriptor(child_fd)
            finally:
                os.close(child_fd)
        elif stat.S_ISREG(metadata.st_mode):
            descriptor = _open_regular(directory_fd, entry.name, metadata)
            try:
                os.fsync(descriptor)
            except OSError as error:
                raise StagingError("staged file cannot be synced") from error
            finally:
                os.close(descriptor)
        else:
            raise StagingError("unsafe staged file")
    try:
        os.fsync(directory_fd)
    except OSError as error:
        raise StagingError("staging directory cannot be synced") from error


def _remove_tree_descriptor(directory_fd: int) -> None:
    try:
        entries = sorted(os.scandir(directory_fd), key=lambda entry: entry.name)
    except OSError as error:
        raise StagingError("unsafe staged cleanup") from error
    for entry in entries:
        try:
            metadata = entry.stat(follow_symlinks=False)
        except OSError as error:
            raise StagingError("unsafe staged cleanup") from error
        if stat.S_ISDIR(metadata.st_mode):
            child_fd, _ = _open_directory(directory_fd, entry.name, create=False)
            try:
                if _identity(os.fstat(child_fd)) != _identity(metadata):
                    raise StagingError("staged directory identity changed")
                _remove_tree_descriptor(child_fd)
            finally:
                os.close(child_fd)
            current = os.stat(entry.name, dir_fd=directory_fd, follow_symlinks=False)
            if _identity(current) != _identity(metadata) or not stat.S_ISDIR(current.st_mode):
                raise StagingError("staged directory identity changed")
            os.rmdir(entry.name, dir_fd=directory_fd)
        elif stat.S_ISREG(metadata.st_mode):
            descriptor = _open_regular(directory_fd, entry.name, metadata)
            os.close(descriptor)
            current = os.stat(entry.name, dir_fd=directory_fd, follow_symlinks=False)
            if _identity(current) != _identity(metadata) or not stat.S_ISREG(current.st_mode):
                raise StagingError("staged file identity changed")
            os.unlink(entry.name, dir_fd=directory_fd)
        else:
            raise StagingError("unsafe staged cleanup")
    try:
        os.fsync(directory_fd)
    except OSError as error:
        raise StagingError("unsafe staged cleanup") from error


class SiblingStage:
    """Promote one private sibling under the trusted-owner filesystem boundary."""

    def __init__(
        self,
        destination: Path,
        *,
        expected_parent_identity: RootIdentity | None = None,
        forbidden_ancestor_identity: RootIdentity | None = None,
    ) -> None:
        if (
            not isinstance(destination, Path)
            or not destination.is_absolute()
            or not destination.name
        ):
            raise StagingError("unsafe portability destination")
        self.destination = destination
        self.parent = destination.parent
        self._expected_parent_identity = expected_parent_identity
        self._forbidden_ancestor_identity = forbidden_ancestor_identity
        self._parent_fd = -1
        self._parent_identity: tuple[int, int] | None = None
        self._stage_name = f".{destination.name}.portable-stage-{uuid.uuid4().hex}"
        self._stage_fd = -1
        self._stage_identity: tuple[int, int] | None = None
        self._promoted = False

    @property
    def root(self) -> Path:
        self.assert_identity()
        return self.parent / self._stage_name

    @property
    def identity(self) -> tuple[int, int]:
        self.assert_identity()
        assert self._stage_identity is not None
        return self._stage_identity

    def assert_identity(self) -> None:
        if (
            self._stage_fd < 0
            or self._parent_fd < 0
            or self._parent_identity is None
            or self._stage_identity is None
        ):
            raise StagingError("staging directory is unavailable")
        current_parent_fd = -1
        try:
            current_parent_fd = _open_absolute_directory(
                self.parent,
                self._parent_identity,
            )
            parent_path = os.fstat(current_parent_fd)
            parent_opened = os.fstat(self._parent_fd)
            opened = os.fstat(self._stage_fd)
            named = os.stat(
                self._stage_name,
                dir_fd=self._parent_fd,
                follow_symlinks=False,
            )
            if self._forbidden_ancestor_identity is not None and (
                _descriptor_descends_from(
                    current_parent_fd,
                    self._forbidden_ancestor_identity,
                )
                or _descriptor_descends_from(
                    self._parent_fd,
                    self._forbidden_ancestor_identity,
                )
            ):
                raise StagingError("staging directory moved inside its source")
        except (OSError, StagingError) as error:
            raise StagingError("staging directory identity changed") from error
        finally:
            if current_parent_fd >= 0:
                os.close(current_parent_fd)
        if (
            not stat.S_ISDIR(named.st_mode)
            or _identity(parent_path) != self._parent_identity
            or _identity(parent_opened) != self._parent_identity
            or _identity(opened) != self._stage_identity
            or _identity(named) != self._stage_identity
        ):
            raise StagingError("staging directory identity changed")

    def open(self) -> None:
        if self._parent_fd >= 0:
            raise StagingError("staging directory is already open")
        try:
            self._parent_fd = _open_absolute_directory(
                self.parent,
                self._expected_parent_identity,
            )
            metadata = os.fstat(self._parent_fd)
            if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o700:
                raise StagingError("unsafe portability destination parent")
            if self._forbidden_ancestor_identity is not None and _descriptor_descends_from(
                self._parent_fd,
                self._forbidden_ancestor_identity,
            ):
                raise StagingError("portability destination is inside its source")
            self._parent_identity = _identity(metadata)
            try:
                os.stat(self.destination.name, dir_fd=self._parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise StagingError("portability destination already exists")
            os.mkdir(self._stage_name, 0o700, dir_fd=self._parent_fd)
            self._stage_fd, _ = _open_directory(
                self._parent_fd,
                self._stage_name,
                create=False,
            )
            self._stage_identity = _identity(os.fstat(self._stage_fd))
            os.fsync(self._stage_fd)
            os.fsync(self._parent_fd)
            self.assert_identity()
        except (OSError, StagingError) as error:
            self.close()
            if isinstance(error, StagingError):
                raise
            raise StagingError("staging directory is unavailable") from error

    def write_bytes(self, relative: str, payload: bytes) -> None:
        if self._stage_fd < 0 or not isinstance(payload, bytes):
            raise StagingError("staging directory is unavailable")
        self.assert_identity()
        parts = _parts(relative)
        parent_fd = self._stage_fd
        opened: list[int] = []
        try:
            for part in parts[:-1]:
                child_fd, created = _open_directory(parent_fd, part, create=True)
                if created:
                    os.fsync(parent_fd)
                opened.append(child_fd)
                parent_fd = child_fd
            descriptor = os.open(
                parts[-1],
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=parent_fd,
            )
            try:
                _write_all(descriptor, payload)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.fsync(parent_fd)
        except (OSError, StagingError) as error:
            if isinstance(error, StagingError):
                raise
            raise StagingError("staged file cannot be written") from error
        finally:
            for descriptor in reversed(opened):
                os.close(descriptor)
        self.assert_identity()

    def fsync_tree(self) -> None:
        self.assert_identity()
        _fsync_tree_descriptor(self._stage_fd)
        self.assert_identity()

    def promote(self, *, pre_rename: Callable[[], None] | None = None) -> None:
        if self._stage_fd < 0 or self._parent_fd < 0:
            raise StagingError("staging directory is unavailable")
        try:
            self.assert_identity()
            try:
                os.stat(self.destination.name, dir_fd=self._parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise StagingError("portability destination already exists")
            self.fsync_tree()
            self.assert_identity()
            if pre_rename is not None:
                pre_rename()
                self.assert_identity()
            _rename_noreplace(self._parent_fd, self._stage_name, self.destination.name)
            promoted = os.stat(
                self.destination.name,
                dir_fd=self._parent_fd,
                follow_symlinks=False,
            )
            if self._stage_identity is None or _identity(promoted) != self._stage_identity:
                raise StagingError("promoted stage identity changed")
            os.fsync(self._parent_fd)
            self._promoted = True
        except (OSError, StagingError) as error:
            if isinstance(error, StagingError):
                raise
            raise StagingError("staged portability promotion failed") from error

    def close(self) -> None:
        cleanup_error: StagingError | None = None
        if self._parent_fd >= 0 and not self._promoted and self._stage_fd >= 0:
            try:
                self.assert_identity()
                _remove_tree_descriptor(self._stage_fd)
                self.assert_identity()
                os.rmdir(self._stage_name, dir_fd=self._parent_fd)
                os.fsync(self._parent_fd)
            except (OSError, StagingError) as error:
                cleanup_error = (
                    error
                    if isinstance(error, StagingError)
                    else StagingError("unsafe staged cleanup")
                )
        if self._stage_fd >= 0:
            os.close(self._stage_fd)
            self._stage_fd = -1
            self._stage_identity = None
        if self._parent_fd >= 0:
            os.close(self._parent_fd)
            self._parent_fd = -1
            self._parent_identity = None
        if cleanup_error is not None:
            raise cleanup_error


@contextmanager
def sibling_stage(
    destination: Path,
    *,
    expected_parent_identity: RootIdentity | None = None,
    forbidden_ancestor_identity: RootIdentity | None = None,
) -> Iterator[SiblingStage]:
    stage = SiblingStage(
        destination,
        expected_parent_identity=expected_parent_identity,
        forbidden_ancestor_identity=forbidden_ancestor_identity,
    )
    stage.open()
    try:
        yield stage
    finally:
        stage.close()
