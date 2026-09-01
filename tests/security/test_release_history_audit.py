from __future__ import annotations

import json
from dataclasses import fields
from hashlib import sha256
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


def write_history_allowlist(
    repository: Path,
    *,
    blob_sha256: str,
    path: str,
    rule: str,
) -> None:
    release = repository / "release"
    release.mkdir(exist_ok=True)
    (release / "public-history-allowlist.json").write_text(
        json.dumps(
            {
                "policy_version": 1,
                "entries": [
                    {
                        "blob_sha256": blob_sha256,
                        "path": path,
                        "reason": "reviewed-public-fixture-redacted-in-current-tree",
                        "rule": rule,
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


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


def test_history_allowlist_suppresses_only_the_exact_reviewed_blob(tmp_path: Path) -> None:
    repository = tmp_path / "synthetic-history"
    repository.mkdir()
    git(repository, "init")
    git(repository, "config", "user.name", "Synthetic Test")
    git(repository, "config", "user.email", "synthetic@example.invalid")
    denylist = tmp_path / "denylist.txt"
    denylist.write_text("unrelated-history-canary\n", encoding="utf-8")
    private_ip = ".".join(("192", "168", "1", "10"))
    path = "reviewed.txt"
    (repository / path).write_text(private_ip, encoding="utf-8")
    git(repository, "add", path)
    git(repository, "commit", "-m", "add reviewed fixture")
    git(repository, "rm", path)
    git(repository, "commit", "-m", "remove reviewed fixture")
    digest = sha256(private_ip.encode()).hexdigest()
    write_history_allowlist(
        repository,
        blob_sha256=digest,
        path=path,
        rule="private-ip-address",
    )

    assert audit_history(repository, denylist) == []

    write_history_allowlist(
        repository,
        blob_sha256="0" * 64,
        path=path,
        rule="private-ip-address",
    )

    assert {finding.rule for finding in audit_history(repository, denylist)} == {
        "private-ip-address"
    }

    write_history_allowlist(
        repository,
        blob_sha256=digest,
        path=path,
        rule="private-denylist-term",
    )

    with pytest.raises(ValueError, match="allowlist rule"):
        audit_history(repository, denylist)


def test_history_allowlist_does_not_cover_the_same_blob_at_another_path(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "synthetic-history"
    repository.mkdir()
    git(repository, "init")
    git(repository, "config", "user.name", "Synthetic Test")
    git(repository, "config", "user.email", "synthetic@example.invalid")
    denylist = tmp_path / "denylist.txt"
    denylist.write_text("unrelated-history-canary\n", encoding="utf-8")
    private_ip = ".".join(("192", "168", "1", "10"))
    for path in ("reviewed.txt", "unreviewed.txt"):
        (repository / path).write_text(private_ip, encoding="utf-8")
    git(repository, "add", "reviewed.txt", "unreviewed.txt")
    git(repository, "commit", "-m", "add path-bound fixtures")
    git(repository, "rm", "reviewed.txt", "unreviewed.txt")
    git(repository, "commit", "-m", "remove path-bound fixtures")
    write_history_allowlist(
        repository,
        blob_sha256=sha256(private_ip.encode()).hexdigest(),
        path="reviewed.txt",
        rule="private-ip-address",
    )

    findings = audit_history(repository, denylist)

    assert {finding.path for finding in findings} == {"unreviewed.txt"}
    assert {finding.rule for finding in findings} == {"private-ip-address"}


def test_history_allowlist_rejects_inexact_or_unsafe_entries(tmp_path: Path) -> None:
    repository = tmp_path / "synthetic-history"
    repository.mkdir()
    git(repository, "init")
    git(repository, "config", "user.name", "Synthetic Test")
    git(repository, "config", "user.email", "synthetic@example.invalid")
    denylist = tmp_path / "denylist.txt"
    denylist.write_text("synthetic-history-canary\n", encoding="utf-8")
    (repository / "safe.txt").write_text("synthetic", encoding="utf-8")
    git(repository, "add", "safe.txt")
    git(repository, "commit", "-m", "add safe fixture")
    write_history_allowlist(
        repository,
        blob_sha256="0" * 64,
        path="../safe.txt",
        rule="absolute-home-path",
    )

    with pytest.raises(ValueError, match="allowlist path"):
        audit_history(repository, denylist)
