import ast
import inspect
import json
import os
import stat
from pathlib import Path

import open_brain.profile as profile_module
import pytest
from open_brain.profile import (
    ProfileError,
    compile_single_user_local,
    open_existing_single_user_local,
)
from open_brain_engine.engine import ProviderMode

TENANT = "tenant_123e4567-e89b-42d3-a456-426614174000"
ACTOR = "actor_123e4567-e89b-42d3-a456-426614174001"
ROLE = "role_123e4567-e89b-42d3-a456-426614174002"
ROLE_CLAIM = "role_claim_123e4567-e89b-42d3-a456-426614174003"


def _identity(*, actor_id: str = ACTOR) -> dict[str, object]:
    return {
        "tenant_id": TENANT,
        "owner_actor_id": actor_id,
        "owner_role_claim": {
            "role_claim_id": ROLE_CLAIM,
            "tenant_id": TENANT,
            "actor_id": actor_id,
            "role_id": ROLE,
            "capabilities": ["canonical.publish", "capture.accept", "space.write"],
        },
    }


def _brain_toml(identity: dict[str, object]) -> str:
    claim = identity["owner_role_claim"]
    assert isinstance(claim, dict)
    return (
        "layout_version = 1\n"
        'profile = "single-user-local"\n'
        f'tenant_id = "{identity["tenant_id"]}"\n'
        f'owner_actor_id = "{identity["owner_actor_id"]}"\n'
        f'owner_role_id = "{claim["role_id"]}"\n'
        f'owner_role_claim_id = "{claim["role_claim_id"]}"\n'
        'owner_capabilities = ["canonical.publish", "capture.accept", "space.write"]\n'
    )


def test_profile_imports_only_the_public_engine_surface() -> None:
    tree = ast.parse(inspect.getsource(profile_module))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("open_brain")
    }

    assert imports == {"open_brain_engine.engine"}


def test_single_user_local_compiles_one_root_with_stable_identities_and_none_provider(
    tmp_path: Path,
) -> None:
    root = tmp_path / "brain"

    first = compile_single_user_local(root)
    second = compile_single_user_local(root)

    assert first.root == root
    assert first.tenant_id == second.tenant_id
    assert first.owner_actor_id == second.owner_actor_id
    assert first.owner_role_claim["role_claim_id"] == second.owner_role_claim["role_claim_id"]
    assert first.provider_mode is ProviderMode.NONE
    assert not (root / ".open-brain" / "identity.json").exists()
    assert (root / "brain.toml").read_text(encoding="utf-8") == _brain_toml(
        {
            "tenant_id": first.tenant_id,
            "owner_actor_id": first.owner_actor_id,
            "owner_role_claim": dict(first.owner_role_claim),
        }
    )


def test_layout_only_profile_migrates_verified_legacy_identity_without_changing_ids(
    tmp_path: Path,
) -> None:
    root = tmp_path / "brain"
    legacy = _identity()
    (root / ".open-brain").mkdir(parents=True)
    (root / "brain.toml").write_text("layout_version = 1\n", encoding="utf-8")
    (root / ".open-brain" / "identity.json").write_bytes(
        json.dumps(legacy, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )

    profile = compile_single_user_local(root)

    assert profile.tenant_id == TENANT
    assert profile.owner_actor_id == ACTOR
    assert profile.owner_role_claim["role_id"] == ROLE
    assert profile.owner_role_claim["role_claim_id"] == ROLE_CLAIM
    assert (root / "brain.toml").read_text(encoding="utf-8") == _brain_toml(legacy)
    assert not (root / ".open-brain" / "identity.json").exists()


def test_matching_legacy_identity_is_retired_and_mismatch_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    matching = _identity()
    (root / ".open-brain").mkdir(parents=True)
    (root / "brain.toml").write_text(_brain_toml(matching), encoding="utf-8")
    legacy_path = root / ".open-brain" / "identity.json"
    legacy_path.write_bytes(json.dumps(matching, sort_keys=True, separators=(",", ":")).encode())

    compile_single_user_local(root)

    assert not legacy_path.exists()
    legacy_path.write_bytes(
        json.dumps(
            _identity(actor_id="actor_123e4567-e89b-42d3-a456-426614174010"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )
    with pytest.raises(ProfileError, match="disagree"):
        compile_single_user_local(root)
    assert (root / "brain.toml").read_text(encoding="utf-8") == _brain_toml(matching)


def test_existing_portable_content_without_identity_does_not_regenerate_ids(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    (root / "content" / "spaces" / "studio").mkdir(parents=True)
    (root / "content" / "spaces" / "studio" / "_space.md").write_text("content\n")
    os.chmod(root, 0o755)
    original_mode = stat.S_IMODE(root.stat().st_mode)

    with pytest.raises(ProfileError, match="identity is missing"):
        compile_single_user_local(root)

    assert not (root / "brain.toml").exists()
    assert not (root / ".open-brain").exists()
    assert not (root / "history").exists()
    assert not (root / "sources").exists()
    assert stat.S_IMODE(root.stat().st_mode) == original_mode


@pytest.mark.parametrize(
    ("internal", "external_child"), ((".open-brain", "indexes"), (".open-brain/indexes", "child"))
)
def test_profile_rejects_poisoned_internal_components_without_mutating_outside_root(
    tmp_path: Path, internal: str, external_child: str
) -> None:
    root = tmp_path / "brain"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o755)
    if internal == ".open-brain/indexes":
        (root / ".open-brain").mkdir()
    (root / internal).symlink_to(outside, target_is_directory=True)
    before_mode = stat.S_IMODE(outside.stat().st_mode)

    with pytest.raises(ProfileError, match="profile|unavailable"):
        compile_single_user_local(root)

    assert stat.S_IMODE(outside.stat().st_mode) == before_mode
    assert not (outside / external_child).exists()
    assert not (root / "brain.toml").exists()


def test_profile_layout_creation_stays_on_pinned_descriptor_after_path_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "brain"
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o755)
    outside_mode = stat.S_IMODE(outside.stat().st_mode)
    original_open_child = profile_module._open_child_directory
    swapped = False

    def swap_after_preflight(parent_fd: int, name: str, *, create: bool) -> int | None:
        nonlocal swapped
        if create and name == "indexes" and not swapped:
            swapped = True
            (root / ".open-brain").rename(root / ".open-brain-pinned")
            (root / ".open-brain").symlink_to(outside, target_is_directory=True)
        return original_open_child(parent_fd, name, create=create)

    monkeypatch.setattr(profile_module, "_open_child_directory", swap_after_preflight)

    with pytest.raises(ProfileError, match="unsafe"):
        compile_single_user_local(root)

    assert swapped is True
    assert stat.S_IMODE(outside.stat().st_mode) == outside_mode
    assert list(outside.iterdir()) == []
    assert (root / ".open-brain-pinned" / "indexes").is_dir()


def test_open_existing_single_user_local_requires_existing_portable_identity_without_creation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "brain"

    with pytest.raises(ProfileError, match="identity is missing|unavailable"):
        open_existing_single_user_local(root)

    assert not root.exists()


def test_open_existing_single_user_local_reports_layout_only_identity_as_profile_error(
    tmp_path: Path,
) -> None:
    root = tmp_path / "brain"
    root.mkdir(mode=0o700)
    (root / "brain.toml").write_text("layout_version = 1\n", encoding="utf-8")

    with pytest.raises(ProfileError, match="portable identity is missing"):
        open_existing_single_user_local(root)
