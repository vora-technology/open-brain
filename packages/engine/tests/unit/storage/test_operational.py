from __future__ import annotations

from pathlib import Path

import pytest
from open_brain_engine.storage.filesystem import StorageError, capture_root_identity
from open_brain_engine.storage.operational import confined_unlink


def test_confined_unlink_removes_only_regular_files_within_the_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    nested = root / "state"
    nested.mkdir()
    target = nested / "receipt.json"
    target.write_text("{}", encoding="utf-8")
    identity = capture_root_identity(root)

    assert confined_unlink(
        root=root,
        relative="state/receipt.json",
        expected_root_identity=identity,
        require_existing=True,
    )
    assert not target.exists()

    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    target.symlink_to(outside)

    with pytest.raises(StorageError, match="unsafe storage target"):
        confined_unlink(
            root=root,
            relative="state/receipt.json",
            expected_root_identity=identity,
        )
