"""Public root-confined storage capabilities for bounded operational state."""

from .filesystem import (
    RootIdentity,
    StorageError,
    WriteState,
    atomic_replace,
    atomic_write_new,
    capture_root_identity,
    confined_unlink,
    read_confined,
    read_confined_tree,
)
from .locks import FileLease, LockBusyError

__all__ = [
    "RootIdentity",
    "StorageError",
    "WriteState",
    "FileLease",
    "LockBusyError",
    "atomic_replace",
    "atomic_write_new",
    "capture_root_identity",
    "confined_unlink",
    "read_confined",
    "read_confined_tree",
]
