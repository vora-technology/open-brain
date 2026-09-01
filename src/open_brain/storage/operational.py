"""Public root-confined storage capabilities for bounded operational state."""

from .filesystem import (
    RootIdentity,
    StorageError,
    WriteState,
    atomic_replace,
    atomic_write_new,
    read_confined,
)

__all__ = [
    "RootIdentity",
    "StorageError",
    "WriteState",
    "atomic_replace",
    "atomic_write_new",
    "read_confined",
]
