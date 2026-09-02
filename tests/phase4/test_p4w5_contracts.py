from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from tools.phase4.readiness_preflight import PHASE4_READINESS_WAVES, ReadinessResult

ROOT = Path(__file__).parents[2]
WORKSTREAM = (
    ROOT
    / "docs/ai/workstreams"
    / (
        "20260901-open-brain-public-execute-goal-63-through-phase-4-"
        "p4a-p4b-and-p4c-with-independently-reviewed-pack-8a3f9b"
    )
)
READINESS_SNAPSHOT_SHA256 = "753a1635aa2be81f3ebe6b3723dbc8e46a6d6aa46f1b39003b9d9c39da769d1b"


def test_one_shot_readiness_snapshot_is_immutable_and_reusable() -> None:
    path = WORKSTREAM / "P4-READINESS-SNAPSHOT.json"
    payload = path.read_bytes()
    value = json.loads(payload)
    result = ReadinessResult.from_dict(value)

    assert sha256(payload).hexdigest() == READINESS_SNAPSHOT_SHA256
    assert result.to_dict() == value
    assert result.signing.ready is True
    assert result.macos_arm64.ready is True
    assert result.disk_capacity.ready is True
    assert result.linux_x86_64.ready is False
    assert result.notarization.ready is False
    assert result.recovery_access.ready is False
    for wave in PHASE4_READINESS_WAVES:
        assert result.for_wave(wave) is result


def test_readiness_snapshot_gitleaks_exception_is_exact_and_audited() -> None:
    relative = (WORKSTREAM / "P4-READINESS-SNAPSHOT.json").relative_to(ROOT).as_posix()
    fingerprint = (
        "638ff2d57b5553ea50fc98648053d1cd11793712:"
        f"{relative}:generic-api-key:13"
    )
    ignore_lines = (ROOT / ".gitleaksignore").read_text(encoding="utf-8").splitlines()
    release_workflow = (ROOT / ".github/workflows/release-audit.yml").read_text(
        encoding="utf-8"
    )

    assert ignore_lines.count(fingerprint) == 1
    assert '      - ".gitleaksignore"' in release_workflow


def test_review_binding_separates_source_candidate_from_evidence_closure() -> None:
    plan = (ROOT / "docs/plans/phase-4-physical-split-native-artifacts-and-cutover.md").read_text(
        encoding="utf-8"
    )
    decisions = (WORKSTREAM / "DECISIONS.md").read_text(encoding="utf-8")

    assert "reviewer binds the source SHA, artifact digests, manifest, host evidence" in plan
    assert "## D-031: bind review to source and reset dispatch budgets by milestone" in decisions
    assert "A docs-only\n  evidence successor does not invalidate that verdict" in decisions
    assert "## D-050: quiesce native upgrades and bind cleanup to trusted enrollment" in decisions
    assert "## D-051: isolate native source and make supervisor quiescence explicit" in decisions
    assert "independent reviewer accepts its exact source candidate" in decisions


def test_p4w5_native_toolchain_and_runner_images_are_exact() -> None:
    toolchain = json.loads((ROOT / "release/phase4-toolchain.json").read_text(encoding="utf-8"))
    primary = toolchain["native"]["primary"]
    fallback = toolchain["native"]["fallback"]

    assert toolchain["native"]["build_python"] == "3.12"
    assert primary == {
        "hooks_name": "pyinstaller-hooks-contrib",
        "hooks_version": "2026.7",
        "mode": "onedir",
        "name": "PyInstaller",
        "version": "6.22.2",
    }
    assert fallback == {
        "activation": "bounded-pyinstaller-failure-gate",
        "mode": "standalone",
        "name": "Nuitka",
        "version": "4.2",
    }
    assert toolchain["runners"] == {
        "linux-x86_64": {
            "architecture": "x86_64",
            "image": "ubuntu-24.04",
            "status": "verified-from-successful-ci-log",
        },
        "macos-arm64": {
            "architecture": "arm64",
            "image": "macos-14-arm64",
            "status": "verified-from-successful-ci-log",
        },
    }

    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    exact_source = "${{ github.event.pull_request.head.sha || github.sha }}"
    macos_job = workflow.split("\n  native-build-macos:\n", maxsplit=1)[1].split(
        "\n  native-build-linux:\n", maxsplit=1
    )[0]
    linux_job = workflow.split("\n  native-build-linux:\n", maxsplit=1)[1].split(
        "\n  connector-isolation:\n", maxsplit=1
    )[0]
    assert "\n  native-build-macos:\n    runs-on: macos-14\n" in workflow
    assert "\n  native-build-linux:\n    runs-on: ubuntu-24.04\n" in workflow
    for job in (macos_job, linux_job):
        assert f"ref: {exact_source}" in job
        assert f"P4W5_SOURCE_SHA={exact_source}" in job
    assert "native-build-linux:\n    runs-on: ubuntu-latest" not in workflow


def test_p4w5_preflight_is_focused_and_compositional() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    preflight = makefile.split("p4w5-preflight:", maxsplit=1)[1].split(
        "\np4w5-native:", maxsplit=1
    )[0]

    assert preflight.startswith(" p4w5-focused p4w5-native-config\n")
    assert "actionlint .github/workflows/ci.yml" in preflight
    assert "tools.phase4.move_manifest validate --root ." in preflight
    assert "ruff check $(P4W5_TOUCHED_PYTHON)" in preflight
    assert "mypy $(P4W5_TOUCHED_PYTHON)" in preflight
    assert "git diff --check" in preflight
    assert "make verify" not in preflight
    assert "make phase4-contracts" not in preflight
