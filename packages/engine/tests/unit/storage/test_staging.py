from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest
from open_brain_engine.storage.staging import SiblingStage, StagingError, sibling_stage


def test_promotion_never_replaces_a_target_created_after_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A target created in the preflight-to-commit gap must retain its inode."""
    destination = tmp_path / "imported"
    original_stat = os.stat
    target_inode: int | None = None
    checks = 0

    def create_target_after_preflight(
        path: str | os.PathLike[str],
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        nonlocal checks, target_inode
        if path == destination.name and dir_fd is not None:
            checks += 1
            if checks == 2:
                destination.mkdir()
                target_inode = destination.stat().st_ino
                raise FileNotFoundError(errno.ENOENT, "synthetic absent target", path)
        return original_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(os, "stat", create_target_after_preflight)

    with sibling_stage(destination) as stage:
        stage.write_bytes("brain.toml", b"synthetic\n")
        with pytest.raises(StagingError, match="already exists"):
            stage.promote()

    assert target_inode is not None
    assert destination.stat().st_ino == target_inode
    assert not list(tmp_path.glob(".imported.portable-stage-*"))


def test_stage_name_replacement_is_neither_promoted_nor_deleted(tmp_path: Path) -> None:
    destination = tmp_path / "imported"
    stage = SiblingStage(destination)
    stage.open()
    stage.write_bytes("brain.toml", b"validated stage\n")
    stage_path = stage.root
    original_stage = tmp_path / "original-stage"
    stage_path.rename(original_stage)
    stage_path.mkdir()
    victim = stage_path / "victim.txt"
    victim.write_text("must survive", encoding="utf-8")

    with pytest.raises(StagingError, match="identity changed"):
        stage.promote()
    with pytest.raises(StagingError, match="identity changed"):
        stage.close()

    assert not destination.exists()
    assert victim.read_text(encoding="utf-8") == "must survive"
    assert (original_stage / "brain.toml").read_bytes() == b"validated stage\n"
