"""Verify built wheel and sdist members against the Phase 0 artifact policy."""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
import tarfile
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast


@dataclass(frozen=True)
class ArtifactPolicyFinding:
    """One metadata-only artifact policy mismatch."""

    artifact: str
    member: str
    rule: str


def _load_policy(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("artifact policy must be an object")
    return cast(dict[str, object], value)


def _mapping(value: object, *, error: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(error)
    return cast(dict[str, object], value)


def _safe_member(name: str) -> str:
    return name.replace("\n", "?").replace("\r", "?")


def _archive_members(path: Path) -> tuple[str, tuple[str, ...]]:
    if path.suffix == ".whl" and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            members = tuple(info.filename for info in archive.infolist() if not info.is_dir())
        return "wheel", members
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:
            raw_members = tuple(member.name for member in archive.getmembers() if member.isfile())
        roots = {PurePosixPath(member).parts[0] for member in raw_members if member}
        if len(roots) != 1:
            raise ValueError("sdist must have one root directory")
        members = tuple(
            PurePosixPath(*PurePosixPath(member).parts[1:]).as_posix()
            for member in raw_members
        )
        return "sdist", members
    raise ValueError(f"unsupported artifact: {path.name}")


def _distribution_configs(policy: dict[str, object]) -> dict[str, dict[str, object]]:
    raw = _mapping(
        policy.get("python_distributions"),
        error="artifact policy distributions are missing",
    )
    if not raw:
        raise ValueError("artifact policy distributions are missing")
    distributions: dict[str, dict[str, object]] = {}
    for name, value in raw.items():
        if not name or "/" in name or not isinstance(value, dict):
            raise ValueError("artifact policy distribution is invalid")
        distributions[name] = cast(dict[str, object], value)
    return distributions


def _distribution_config(policy: dict[str, object], distribution: str) -> dict[str, object]:
    distributions = _distribution_configs(policy)
    if distribution not in distributions:
        raise ValueError("artifact policy distribution is missing")
    return distributions[distribution]


def _artifact_config(
    policy: dict[str, object], distribution: str, kind: str
) -> dict[str, object]:
    distribution_config = _distribution_config(policy, distribution)
    artifacts = distribution_config.get("artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get(kind), dict):
        raise ValueError("artifact policy is missing a build kind")
    return cast(dict[str, object], artifacts[kind])


def _artifact_name_pattern(
    policy: dict[str, object], distribution: str, kind: str
) -> str:
    distribution_config = _distribution_config(policy, distribution)
    patterns = _mapping(
        distribution_config.get("artifact_name_patterns"),
        error="artifact policy artifact name patterns are missing",
    )
    pattern = patterns.get(kind)
    if not isinstance(pattern, str) or not pattern or "/" in pattern or "\\" in pattern:
        raise ValueError("artifact policy artifact name pattern is invalid")
    return pattern


def _patterns(config: dict[str, object], key: str) -> tuple[str, ...]:
    value = config.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"artifact policy {key} must be a string list")
    return tuple(value)


def _required_members(config: dict[str, object], project_root: Path) -> tuple[str, ...]:
    required = set(_patterns(config, "required_members"))
    trees = config.get("required_trees")
    if not isinstance(trees, list):
        raise ValueError("artifact policy required_trees must be a list")
    for tree in trees:
        if not isinstance(tree, dict):
            raise ValueError("artifact policy required tree must be an object")
        source = tree.get("source")
        destination = tree.get("destination")
        if not isinstance(source, str) or not isinstance(destination, str):
            raise ValueError("artifact policy required tree is malformed")
        source_root = project_root / source
        if not source_root.is_dir() or source_root.is_symlink():
            raise ValueError("artifact policy required tree source is missing")
        for path in source_root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                relative = path.relative_to(source_root).as_posix()
                required.add(PurePosixPath(destination, relative).as_posix())
    return tuple(sorted(required))


def _relative_manifest_path(value: object, *, error: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(error)
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValueError(error)
    return path


def _manifest_member(current_path: str, *, project_root: str, kind: str) -> str:
    source_prefix = f"{project_root}/src/"
    project_prefix = f"{project_root}/"
    if current_path.startswith(source_prefix):
        relative = current_path.removeprefix(project_prefix)
        return relative if kind == "sdist" else relative.removeprefix("src/")
    if current_path.startswith(project_prefix):
        return current_path.removeprefix(project_prefix)
    return current_path


def _manifest_members(
    policy_path: Path,
    policy: dict[str, object],
    distribution: str,
    kind: str,
) -> tuple[str, ...]:
    config = _mapping(
        policy.get("canonical_manifest"),
        error="artifact policy canonical manifest is missing",
    )
    manifest_relative = _relative_manifest_path(
        config.get("path"),
        error="artifact policy canonical manifest path is invalid",
    )
    distribution_config = _distribution_config(policy, distribution)
    project_relative = _relative_manifest_path(
        distribution_config.get("project_root"),
        error="artifact policy project root is invalid",
    )
    raw_rewrites = _mapping(
        distribution_config.get("member_rewrites"),
        error="artifact policy member rewrites are invalid",
    )
    rewrites = _mapping(
        raw_rewrites.get(kind),
        error="artifact policy member rewrites are invalid",
    )
    if any(not isinstance(value, str) for value in rewrites.values()):
        raise ValueError("artifact policy member rewrite is invalid")

    repository_root = policy_path.resolve().parent.parent
    manifest = _load_policy(repository_root / manifest_relative)
    files = _mapping(manifest.get("files"), error="canonical manifest files are invalid")
    phase4 = _mapping(manifest.get("phase4"), error="canonical manifest phase4 is invalid")
    subjects = _mapping(
        phase4.get("subjects"),
        error="canonical manifest subjects are invalid",
    )
    label = f"{distribution}-{kind}"
    members: set[str] = set()
    used_rewrites: set[str] = set()
    for raw_record in (*files.values(), *subjects.values()):
        record = _mapping(raw_record, error="canonical manifest record is invalid")
        disposition = record.get("artifact_disposition")
        if not isinstance(disposition, list) or any(
            not isinstance(item, str) for item in disposition
        ):
            raise ValueError("canonical manifest artifact disposition is invalid")
        if label not in disposition:
            continue
        current = _relative_manifest_path(
            record.get("current_path"),
            error="canonical manifest current path is invalid",
        ).as_posix()
        member = _manifest_member(
            current,
            project_root=project_relative.as_posix(),
            kind=kind,
        )
        if member in rewrites:
            used_rewrites.add(member)
            member = cast(str, rewrites[member])
        else:
            member = member.partition("#")[0]
        normalized = _relative_manifest_path(
            member,
            error="canonical manifest artifact member is invalid",
        ).as_posix()
        members.add(normalized)
    if used_rewrites != set(rewrites):
        raise ValueError("artifact policy member rewrite is stale")
    if not members:
        raise ValueError("canonical manifest artifact membership is empty")
    return tuple(sorted(members))


def _required_members_for_kind(
    policy_path: Path,
    policy: dict[str, object],
    distribution: str,
    kind: str,
) -> tuple[str, ...]:
    config = _artifact_config(policy, distribution, kind)
    repository_root = policy_path.resolve().parent.parent
    configured = _required_members(config, repository_root)
    declared = _manifest_members(policy_path, policy, distribution, kind)
    if not set(configured) <= set(declared):
        raise ValueError("artifact policy required members contradict the canonical manifest")
    return declared


def required_members_for_policy(
    policy_path: Path, distribution: str, kind: str
) -> tuple[str, ...]:
    """Resolve every required member, including complete resource trees."""
    policy = _load_policy(policy_path)
    return _required_members_for_kind(policy_path, policy, distribution, kind)


def _is_forbidden(member: str, patterns: tuple[str, ...]) -> bool:
    path = PurePosixPath(member)
    if path.is_absolute() or ".." in path.parts:
        return True
    return any(fnmatch.fnmatchcase(member, pattern) for pattern in patterns)


def _artifact_coordinate_from_name(
    policy: dict[str, object],
    name: str,
    *,
    kind: str | None = None,
) -> tuple[str, str] | None:
    matches = [
        (distribution, candidate_kind)
        for distribution in _distribution_configs(policy)
        for candidate_kind in ("wheel", "sdist")
        if (kind is None or candidate_kind == kind)
        and fnmatch.fnmatchcase(
            name,
            _artifact_name_pattern(policy, distribution, candidate_kind),
        )
    ]
    if len(matches) > 1:
        raise ValueError("artifact policy artifact name patterns overlap")
    return matches[0] if matches else None


def verify_artifacts(policy_path: Path, artifacts: Sequence[Path]) -> list[ArtifactPolicyFinding]:
    """Verify required and forbidden member names without reading artifact content."""
    policy = _load_policy(policy_path)
    findings: list[ArtifactPolicyFinding] = []
    expected_coordinates: set[tuple[str, str]] = set()
    for distribution in _distribution_configs(policy):
        for kind in ("wheel", "sdist"):
            _artifact_config(policy, distribution, kind)
            _artifact_name_pattern(policy, distribution, kind)
            expected_coordinates.add((distribution, kind))
    seen_coordinates: set[tuple[str, str]] = set()
    for artifact in artifacts:
        if not artifact.is_file():
            findings.append(ArtifactPolicyFinding(artifact.name, "<artifact>", "missing-artifact"))
            coordinate = _artifact_coordinate_from_name(policy, artifact.name)
            if coordinate is not None:
                seen_coordinates.add(coordinate)
            continue
        kind, raw_members = _archive_members(artifact)
        coordinate = _artifact_coordinate_from_name(policy, artifact.name, kind=kind)
        if coordinate is None:
            findings.append(
                ArtifactPolicyFinding(
                    artifact.name,
                    "<artifact>",
                    "unknown-artifact-distribution",
                )
            )
            continue
        distribution, _ = coordinate
        if coordinate in seen_coordinates:
            findings.append(
                ArtifactPolicyFinding(
                    artifact.name,
                    "<artifact>",
                    "duplicate-artifact-coordinate",
                )
            )
        seen_coordinates.add(coordinate)
        members = tuple(_safe_member(member) for member in raw_members)
        if len(set(members)) != len(members):
            findings.append(
                ArtifactPolicyFinding(artifact.name, "<artifact>", "duplicate-member")
            )
        config = _artifact_config(policy, distribution, kind)
        required = _required_members_for_kind(policy_path, policy, distribution, kind)
        forbidden = _patterns(config, "forbidden_member_patterns")
        generated = _patterns(config, "generated_member_patterns")
        for required_member in required:
            if required_member not in members:
                findings.append(
                    ArtifactPolicyFinding(artifact.name, required_member, "missing-required-member")
                )
        for member in members:
            if _is_forbidden(member, forbidden):
                findings.append(
                    ArtifactPolicyFinding(artifact.name, member, "forbidden-member")
                )
            elif member not in required and not any(
                fnmatch.fnmatchcase(member, pattern) for pattern in generated
            ):
                findings.append(
                    ArtifactPolicyFinding(artifact.name, member, "undeclared-member")
                )
    for distribution, kind in sorted(expected_coordinates - seen_coordinates):
        findings.append(
            ArtifactPolicyFinding(
                "<artifacts>",
                f"{distribution}-{kind}",
                "missing-artifact-coordinate",
            )
        )
    return sorted(set(findings), key=lambda item: (item.artifact, item.member, item.rule))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, nargs="+", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        findings = verify_artifacts(args.policy, args.artifacts)
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(f"artifact policy error: {exc}", file=sys.stderr)
        return 2
    for finding in findings:
        print(f"{finding.artifact}:{finding.member}: {finding.rule}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
