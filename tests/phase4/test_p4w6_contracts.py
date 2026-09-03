from __future__ import annotations

import json
import stat
from hashlib import sha256
from pathlib import Path
from typing import cast

from tools.phase4.release_candidate import EXPECTED_RELEASE_ARTIFACT_COORDINATES

ROOT = Path(__file__).resolve().parents[2]
WORKSTREAM = (
    ROOT
    / "docs/ai/workstreams"
    / (
        "20260901-open-brain-public-execute-goal-63-through-phase-4-"
        "p4a-p4b-and-p4c-with-independently-reviewed-pack-8a3f9b"
    )
)
SNAPSHOT_SHA256 = "753a1635aa2be81f3ebe6b3723dbc8e46a6d6aa46f1b39003b9d9c39da769d1b"
UPLOAD_ARTIFACT_V7 = "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
DOWNLOAD_ARTIFACT_V8 = "3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"


def test_p4w6_make_targets_are_separate_from_frozen_p4w5_targets() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    for target in (
        "p4w6-focused:",
        "p4w6-python:",
        "p4w6-linux:",
        "p4w6-macos-compatibility:",
        "p4w6-macos:",
        "p4w6-clean-host:",
        "p4w6-assemble:",
        "p4w6-verify:",
    ):
        assert target in makefile
    p4w6_section = makefile[makefile.index("P4W6_FOCUSED_TESTS") :]
    assert "make p4w5" not in p4w6_section
    assert "tools.phase4.release_assembly build-linux" in p4w6_section
    assert "tools.phase4.release_assembly build-macos" in p4w6_section
    assert "tools/phase4/clean_host_lifecycle.sh" in p4w6_section
    assert '\t@tools/phase4/clean_host_lifecycle.sh' in p4w6_section
    assert "tools.phase4.release_assembly assemble" in p4w6_section
    assert "tools.phase4.release_assembly verify" in p4w6_section


def test_p4w6_ci_builds_once_then_runs_exact_linux_archive_on_three_hosts() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "p4w6-python-artifacts:" in workflow
    assert "p4w6-linux-build:" in workflow
    assert "p4w6-linux-clean-host:" in workflow
    assert "p4w6-macos-14-compatibility:" in workflow
    assert "container-image: [ubuntu:24.04, ubuntu:26.04, debian:13]" in workflow
    assert f"actions/upload-artifact@{UPLOAD_ARTIFACT_V7} # v7.0.1" in workflow
    assert f"actions/download-artifact@{DOWNLOAD_ARTIFACT_V8} # v8.0.1" in workflow
    assert "open-brain-0.1.0-linux-x86_64.tar.gz" in workflow
    assert "open-brain-0.1.0-macos-arm64-compatibility.tar.gz" in workflow
    assert "runs-on: macos-14" in workflow
    assert "P4W6_SOURCE_SHA=${{ github.event.pull_request.head.sha || github.sha }}" in workflow
    assert "p4w6-clean-host-${{ strategy.job-index }}-" in workflow
    assert "p4w6-clean-host-${{ matrix.container-image }}-" not in workflow


def test_release_policy_declares_unpublished_media_manifest_and_exact_evidence_set() -> None:
    policy = json.loads((ROOT / "release/v0-artifact-policy.json").read_bytes())
    toolchain = json.loads((ROOT / "release/phase4-toolchain.json").read_bytes())
    release = cast(dict[str, object], policy["release_candidate"])

    assert release["candidate_id"] == "candidate_native-p4w6"
    assert release["version"] == "0.1.0"
    assert release["status"] == "unpublished"
    assert release["required_coordinates"] == list(EXPECTED_RELEASE_ARTIFACT_COORDINATES)
    assert release["native_media"] == {
        "linux-x86_64": {
            "checksum": "sha256",
            "format": "tar.gz",
            "signed": False,
        },
        "macos-arm64": {
            "format": "dmg",
            "hardened_runtime": True,
            "notarized": True,
            "secure_timestamp": True,
            "stapled": True,
        },
    }
    assert toolchain["signing"] == {
        "developer_id_application": "available-on-coordinator",
        "hardened_runtime": "required",
        "identity_output": "prohibited",
        "notary_credentials": "ready-private",
        "notary_output": "bounded-result-only",
        "notarytool": "available",
        "secure_timestamp": "required",
        "stapling": "required",
    }
    assert policy["native_artifacts"]["status"] == "p4w6-unpublished-release-candidate"


def test_p4w6_host_scripts_are_executable_and_snapshot_stays_immutable() -> None:
    for relative in (
        "release/native/install.sh",
        "tools/phase4/clean_host_lifecycle.sh",
        "tools/phase4/supervisor_shim.sh",
        "tools/phase4/unix_request.pl",
    ):
        path = ROOT / relative
        assert path.is_file()
        assert stat.S_IMODE(path.stat().st_mode) == 0o755

    snapshot = (WORKSTREAM / "P4-READINESS-SNAPSHOT.json").read_bytes()
    assert sha256(snapshot).hexdigest() == SNAPSHOT_SHA256
