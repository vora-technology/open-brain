import ast
from pathlib import Path

from open_brain.engine import ProviderMode
from open_brain.profile import compile_single_user_local


def test_profile_imports_only_the_public_engine_surface() -> None:
    source = Path(__file__).parents[3] / "src" / "open_brain" / "profile.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("open_brain")
    }

    assert imports == {"open_brain.engine"}


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
