"""Single-user local profile compilation from one Brain root."""

from __future__ import annotations

import json
import os
import stat
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType

from open_brain.core.ids import portable_canonical_json_bytes
from open_brain.engine.local import LocalEngineContext
from open_brain.providers.base import ProviderMode
from open_brain.storage.filesystem import atomic_write_new, read_confined


class ProfileError(ValueError):
    """A Brain root cannot compile into the safe local profile."""


SingleUserLocalProfile = LocalEngineContext


def compile_single_user_local(
    root: Path, *, starter_spaces: Sequence[str] = ()
) -> SingleUserLocalProfile:
    """Create or reopen one root without replacing stable local identity."""
    if not isinstance(root, Path):
        raise ProfileError("Brain root must be a path")
    candidate = root.expanduser().absolute()
    if candidate.exists() and candidate.is_symlink():
        raise ProfileError("Brain root must not be a symlink")
    try:
        candidate.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(candidate, 0o700)
        absolute_root = candidate.resolve(strict=True)
    except OSError as error:
        raise ProfileError("Brain root is unavailable") from error
    metadata = absolute_root.stat()
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) & 0o022:
        raise ProfileError("Brain root permissions are unsafe")
    normalized_starters = _starter_spaces(starter_spaces)
    _create_layout(absolute_root)
    identity = _load_or_create_identity(absolute_root)
    role_claim = _mapping(identity, "owner_role_claim")
    capabilities = role_claim.get("capabilities")
    assert isinstance(capabilities, list)
    role_claim["capabilities"] = tuple(capabilities)
    return LocalEngineContext(
        root=absolute_root,
        tenant_id=_string(identity, "tenant_id"),
        owner_actor_id=_string(identity, "owner_actor_id"),
        owner_role_claim=MappingProxyType(role_claim),
        provider_mode=ProviderMode.NONE,
        starter_spaces=normalized_starters,
    )


def _create_layout(root: Path) -> None:
    for relative in (
        ".open-brain/indexes",
        ".open-brain/quarantine",
        ".open-brain/run",
        ".open-brain/state",
        "content/spaces",
        "history/decisions",
        "history/proposals",
        "history/publications",
        "sources/blobs/sha256",
        "sources/captures",
    ):
        path = root.joinpath(*relative.split("/"))
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(path, 0o700)
    atomic_write_new(root=root, relative="brain.toml", data=b"layout_version = 1\n")


def _load_or_create_identity(root: Path) -> dict[str, object]:
    payload = read_confined(root=root, relative=".open-brain/identity.json")
    if payload is None:
        identity = _new_identity()
        atomic_write_new(
            root=root,
            relative=".open-brain/identity.json",
            data=portable_canonical_json_bytes(identity),
        )
        return identity
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProfileError("local identity is invalid") from error
    if not isinstance(value, dict):
        raise ProfileError("local identity is invalid")
    _validate_identity(value)
    return value


def _new_identity() -> dict[str, object]:
    tenant_id = _portable_id("tenant")
    actor_id = _portable_id("actor")
    role_claim = {
        "actor_id": actor_id,
        "capabilities": ["canonical.publish", "capture.accept", "space.write"],
        "role_claim_id": _portable_id("role_claim"),
        "role_id": _portable_id("role"),
        "tenant_id": tenant_id,
    }
    value: dict[str, object] = {
        "owner_actor_id": actor_id,
        "owner_role_claim": role_claim,
        "tenant_id": tenant_id,
    }
    _validate_identity(value)
    return value


def _portable_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4()}"


def _validate_identity(value: Mapping[str, object]) -> None:
    if set(value) != {"tenant_id", "owner_actor_id", "owner_role_claim"}:
        raise ProfileError("local identity is invalid")
    tenant_id = _string(value, "tenant_id")
    actor_id = _string(value, "owner_actor_id")
    role_claim = _mapping(value, "owner_role_claim")
    capabilities = role_claim.get("capabilities")
    if (
        set(role_claim) != {"role_claim_id", "tenant_id", "actor_id", "role_id", "capabilities"}
        or role_claim.get("tenant_id") != tenant_id
        or role_claim.get("actor_id") != actor_id
        or not isinstance(capabilities, list)
        or capabilities != sorted(set(capabilities))
        or any(not isinstance(item, str) or not item for item in capabilities)
    ):
        raise ProfileError("local identity is invalid")
    for prefix, identifier in (("tenant", tenant_id), ("actor", actor_id)):
        _validate_portable_id(identifier, prefix)
    for key, prefix in (("role_claim_id", "role_claim"), ("role_id", "role")):
        item = role_claim.get(key)
        if not isinstance(item, str):
            raise ProfileError("local identity is invalid")
        _validate_portable_id(item, prefix)


def _validate_portable_id(value: str, prefix: str) -> None:
    marker = prefix + "_"
    if not value.startswith(marker):
        raise ProfileError("local identity is invalid")
    try:
        parsed = uuid.UUID(value.removeprefix(marker))
    except ValueError as error:
        raise ProfileError("local identity is invalid") from error
    if value != f"{prefix}_{parsed}" or parsed.version != 4:
        raise ProfileError("local identity is invalid")


def _string(value: Mapping[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise ProfileError("local identity is invalid")
    return item


def _mapping(value: Mapping[str, object], key: str) -> dict[str, object]:
    item = value.get(key)
    if not isinstance(item, dict) or any(not isinstance(name, str) for name in item):
        raise ProfileError("local identity is invalid")
    return item


def _starter_spaces(value: Sequence[str]) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ProfileError("starter spaces are invalid")
    result = tuple(item.strip() for item in value)
    if any(not item or len(item) > 120 for item in result) or len(set(result)) != len(result):
        raise ProfileError("starter spaces are invalid")
    return result
