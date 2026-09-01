from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from subprocess import run

import pytest
from pytest import CaptureFixture

from open_brain.dev.public_history_audit import HistoryFinding, audit_history, main


def git(repository: Path, *args: str) -> str:
    result = run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_history_audit_reports_only_commit_path_and_rule_for_removed_content(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    repository = tmp_path / "synthetic-history"
    repository.mkdir()
    git(repository, "init")
    git(repository, "config", "user.name", "Synthetic Test")
    git(repository, "config", "user.email", "synthetic@example.invalid")
    denylist = tmp_path / "denylist.txt"
    canary = "synthetic-private-canary"
    denylist.write_text(f"{canary}\n", encoding="utf-8")
    removed_path = repository / "removed.txt"
    removed_path.write_text(canary, encoding="utf-8")
    git(repository, "add", "removed.txt")
    git(repository, "commit", "-m", "add synthetic fixture")
    commit = git(repository, "rev-parse", "HEAD")
    git(repository, "rm", "removed.txt")
    git(repository, "commit", "-m", "remove synthetic fixture")

    findings = audit_history(repository, denylist)

    assert findings == [
        HistoryFinding(commit=commit, path="removed.txt", rule="private-denylist-term")
    ]
    assert [field.name for field in fields(HistoryFinding)] == ["commit", "path", "rule"]
    assert main(["--repository", str(repository), "--private-denylist", str(denylist)]) == 1
    assert canary not in capsys.readouterr().out


def test_history_audit_redacts_denylisted_path_components(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    repository = tmp_path / "synthetic-history"
    repository.mkdir()
    git(repository, "init")
    git(repository, "config", "user.name", "Synthetic Test")
    git(repository, "config", "user.email", "synthetic@example.invalid")
    denylist = tmp_path / "denylist.txt"
    canary = "synthetic-owner-name"
    denylist.write_text(f"{canary}\n", encoding="utf-8")
    secret_path = repository / f"{canary}-notes.txt"
    secret_path.write_text(canary, encoding="utf-8")
    git(repository, "add", secret_path.name)
    git(repository, "commit", "-m", "add redaction fixture")

    findings = audit_history(repository, denylist)

    assert findings and all(canary not in finding.path for finding in findings)
    assert all(finding.path.startswith("<redacted-path:") for finding in findings)
    assert main(["--repository", str(repository), "--private-denylist", str(denylist)]) == 1
    assert canary not in capsys.readouterr().out


def test_history_audit_fails_closed_for_oversized_and_binary_content(tmp_path: Path) -> None:
    repository = tmp_path / "synthetic-history"
    repository.mkdir()
    git(repository, "init")
    git(repository, "config", "user.name", "Synthetic Test")
    git(repository, "config", "user.email", "synthetic@example.invalid")
    denylist = tmp_path / "denylist.txt"
    canary = "synthetic-private-canary"
    denylist.write_text(f"{canary}\n", encoding="utf-8")
    (repository / "large.bin").write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    (repository / "binary.bin").write_bytes(b"prefix\x00" + canary.encode("utf-8"))
    git(repository, "add", "large.bin", "binary.bin")
    git(repository, "commit", "-m", "add bounded scan fixtures")

    rules = {finding.rule for finding in audit_history(repository, denylist)}

    assert "content-scan-limit-exceeded" in rules
    assert "private-denylist-term" in rules


def test_history_audit_accepts_explicit_no_additional_project_terms_marker(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "synthetic-history"
    repository.mkdir()
    git(repository, "init")
    git(repository, "config", "user.name", "Synthetic Test")
    git(repository, "config", "user.email", "synthetic@example.invalid")
    denylist = tmp_path / "denylist.txt"
    denylist.write_text("# no additional project terms\n", encoding="utf-8")
    (repository / "safe.txt").write_text("synthetic public fixture", encoding="utf-8")
    git(repository, "add", "safe.txt")
    git(repository, "commit", "-m", "add synthetic fixture")

    assert audit_history(repository, denylist) == []
    assert main(["--repository", str(repository), "--private-denylist", str(denylist)]) == 0


def test_history_audit_limits_fail_closed(tmp_path: Path) -> None:
    repository = tmp_path / "synthetic-history"
    repository.mkdir()
    git(repository, "init")
    git(repository, "config", "user.name", "Synthetic Test")
    git(repository, "config", "user.email", "synthetic@example.invalid")
    denylist = tmp_path / "denylist.txt"
    denylist.write_text("synthetic-private-canary\n", encoding="utf-8")
    (repository / "one.txt").write_text("synthetic", encoding="utf-8")
    git(repository, "add", "one.txt")
    git(repository, "commit", "-m", "add limit fixture")

    with pytest.raises(ValueError, match="commit limit"):
        audit_history(repository, denylist, maximum_commits=0)
    with pytest.raises(ValueError, match="blob limit"):
        audit_history(repository, denylist, maximum_blobs=0)
    with pytest.raises(ValueError, match="byte limit"):
        audit_history(repository, denylist, maximum_bytes=0)
