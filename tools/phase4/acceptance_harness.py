"""Reusable isolated-artifact contracts and stable Phase 4 finding codes."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import tarfile
import zipfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final, cast

EXPECTED_RED_SCHEMA: Final = 1


@dataclass(frozen=True, order=True, slots=True)
class Finding:
    code: str
    subject: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "detail": self.detail, "subject": self.subject}


@dataclass(frozen=True, slots=True)
class ArtifactContract:
    subject: str
    required_members: tuple[str, ...]
    forbidden_patterns: tuple[str, ...]
    expected_name: str | None = None
    expected_version: str | None = None


@dataclass(frozen=True, slots=True)
class ImportProbe:
    module_paths: tuple[str, ...]
    sys_path: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AcceptanceContract:
    contract_id: str
    gate: str
    artifacts: tuple[str, ...]
    behaviors: tuple[str, ...]
    forbidden_imports: tuple[str, ...]


CONTRACTS: Final = (
    AcceptanceContract(
        "engine-isolation",
        "P4A",
        ("engine-wheel",),
        ("public-engine-import", "engine-unit-integration"),
        ("open_brain", "open_brain_connectors", "open_brain_legacy"),
    ),
    AcceptanceContract(
        "app-isolation",
        "P4A",
        ("app-wheel", "engine-wheel"),
        (
            "first-value-no-provider",
            "v0-gate-07-sibling-approve-reject-safe-edit-cli-ui",
            "v0-gate-13-space-create-rename-later-route-scoped-all-retrieval",
            "daemon-status-doctor",
            "backup-restore-portable-upgrade-uninstall",
        ),
        ("open_brain_connectors", "open_brain_legacy"),
    ),
    AcceptanceContract(
        "connector-isolation",
        "P4A",
        ("connector-wheel", "app-wheel", "engine-wheel"),
        ("reference-conformance", "isolated-worker", "bounded-capabilities"),
        ("open_brain_legacy",),
    ),
    AcceptanceContract(
        "artifact-membership",
        "P4A/P4B",
        ("all-python-and-native-artifacts",),
        ("required-members", "forbidden-members", "duplicates", "safe-paths"),
        (),
    ),
    AcceptanceContract(
        "identity-compatibility",
        "P4A/P4B",
        ("all-python-and-native-artifacts",),
        ("package-native-doctor-portable-schema-identity",),
        (),
    ),
    AcceptanceContract(
        "clean-host-lifecycle",
        "P4B",
        ("macos-arm64-native", "linux-x86_64-native"),
        (
            "install-init-start-status-capture-review-retrieve",
            "backup-exact-restore-portable-upgrade-rollback",
            "stop-uninstall-residue-no-source-no-system-python",
        ),
        (),
    ),
)


def sanitized_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ if source is None else source)
    for name in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def build_command(project: Path, destination: Path) -> tuple[str, ...]:
    return (
        "uv",
        "build",
        "--no-sources",
        "--project",
        os.fspath(project),
        "--out-dir",
        os.fspath(destination),
    )


def create_environment_command(environment: Path) -> tuple[str, ...]:
    return ("uv", "venv", "--python", "3.12", os.fspath(environment))


def install_command(python: Path, artifacts: Sequence[Path]) -> tuple[str, ...]:
    return (
        "uv",
        "pip",
        "install",
        "--python",
        os.fspath(python),
        "--no-index",
        *(os.fspath(path) for path in artifacts),
    )


def run_checked(
    command: Sequence[str],
    *,
    cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    return runner(
        tuple(command),
        cwd=cwd,
        env=sanitized_environment(),
        check=True,
        capture_output=True,
        text=True,
        timeout=1800,
    )


def _archive_members(path: Path) -> tuple[list[str], Mapping[str, bytes]]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            zip_payloads = {name: archive.read(name) for name in names if name.endswith("METADATA")}
            return names, zip_payloads
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:
            names = archive.getnames()
            tar_payloads: dict[str, bytes] = {}
            for member in archive.getmembers():
                if not member.name.endswith("PKG-INFO") or not member.isfile():
                    continue
                stream = archive.extractfile(member)
                if stream is not None:
                    tar_payloads[member.name] = stream.read()
            return names, tar_payloads
    return [], {}


def _metadata(payloads: Mapping[str, bytes]) -> tuple[str | None, str | None]:
    for payload in payloads.values():
        name = version = None
        for line in payload.decode("utf-8", errors="replace").splitlines():
            if line.startswith("Name: "):
                name = line.removeprefix("Name: ")
            elif line.startswith("Version: "):
                version = line.removeprefix("Version: ")
        if name is not None or version is not None:
            return name, version
    return None, None


def artifact_findings(path: Path, contract: ArtifactContract) -> list[Finding]:
    if not path.is_file():
        return [Finding("P4H001", contract.subject, "artifact is missing")]
    names, payloads = _archive_members(path)
    if not names:
        return [Finding("P4H001", contract.subject, "artifact format is unsupported")]
    findings: list[Finding] = []
    if len(names) != len(set(names)):
        findings.append(Finding("P4H006", contract.subject, "artifact has duplicate members"))
    for name in names:
        member = PurePosixPath(name)
        if member.is_absolute() or ".." in member.parts or "\\" in name:
            findings.append(Finding("P4H005", contract.subject, "artifact has an unsafe member"))
        if any(fnmatch.fnmatch(name, pattern) for pattern in contract.forbidden_patterns):
            findings.append(Finding("P4H002", contract.subject, "artifact has a forbidden member"))
    for required in contract.required_members:
        if required not in names:
            findings.append(Finding("P4H001", contract.subject, "artifact lacks a required member"))
    metadata_name, metadata_version = _metadata(payloads)
    if (contract.expected_name is not None and metadata_name != contract.expected_name) or (
        contract.expected_version is not None and metadata_version != contract.expected_version
    ):
        findings.append(Finding("P4H003", contract.subject, "artifact identity is mismatched"))
    return sorted(set(findings))


def import_probe_findings(probe: ImportProbe, repository_root: Path) -> list[Finding]:
    root = repository_root.resolve()
    for raw in (*probe.module_paths, *probe.sys_path):
        if not raw:
            continue
        try:
            path = Path(raw).resolve()
        except OSError:
            continue
        if path == root or root in path.parents:
            return [
                Finding("P4H004", "isolated-import-probe", "repository source masked isolation")
            ]
    return []


def current_layout_findings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for distribution in ("engine", "app", "connectors", "legacy"):
        if not (root / "packages" / distribution / "pyproject.toml").is_file():
            findings.append(Finding("P4E001", distribution, "distribution root is absent"))
    project: dict[str, object] = {}
    try:
        import tomllib

        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError):
        pass
    tool = project.get("tool")
    uv = tool.get("uv") if isinstance(tool, dict) else None
    workspace = uv.get("workspace") if isinstance(uv, dict) else None
    if not isinstance(workspace, dict) or not workspace.get("members"):
        findings.append(Finding("P4E002", "uv-workspace", "workspace membership is inactive"))
    if (root / "src/open_brain").is_dir():
        findings.append(Finding("P4E003", "src/open_brain", "monolith source tree remains"))
    for artifact in ("engine-wheel", "app-wheel", "connector-wheel"):
        findings.append(
            Finding("P4E004", artifact, "isolated distribution artifact is unavailable")
        )
    for artifact in ("macos-arm64-native", "linux-x86_64-native"):
        findings.append(Finding("P4E005", artifact, "native artifact is unavailable"))
    return sorted(findings)


def expected_red_payload(root: Path) -> dict[str, object]:
    return {
        "schema_version": EXPECTED_RED_SCHEMA,
        "baseline": "current-monolith",
        "findings": [finding.to_dict() for finding in current_layout_findings(root)],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("list-contracts", "inspect-current", "write-expected-red")
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "list-contracts":
        print(json.dumps([contract.contract_id for contract in CONTRACTS]))
        return 0
    payload = expected_red_payload(args.root.resolve())
    if args.command == "write-expected-red":
        if args.output is None:
            raise SystemExit("write-expected-red requires --output")
        args.output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return 0
    findings = cast(list[dict[str, str]], payload["findings"])
    for finding in findings:
        print(json.dumps(finding, sort_keys=True))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
