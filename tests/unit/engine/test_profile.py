from pathlib import Path

from open_brain.profile import compile_single_user_local
from open_brain.providers.base import ProviderMode


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
    assert (root / ".open-brain" / "identity.json").is_file()
    assert (root / "brain.toml").read_text(encoding="utf-8") == "layout_version = 1\n"
