from __future__ import annotations

import ast
import json
import subprocess
import tomllib
import zipfile
from pathlib import Path

import pytest

from tools.phase4.acceptance_harness import build_command, engine_isolation_findings

ROOT = Path(__file__).parents[2]
_IMPORT_DISTRIBUTIONS = {
    "open_brain": "app",
    "open_brain_connectors": "connectors",
    "open_brain_engine": "engine",
    "open_brain_legacy": "legacy",
}
_PROJECT_NAMES = {
    "app": "open-brain",
    "connectors": "open-brain-connectors",
    "engine": "open-brain-engine",
}


def _static_distribution_imports(source_root: Path, *, owner: str) -> set[str]:
    imports: set[str] = set()
    for path in source_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: tuple[str, ...] = ()
            if isinstance(node, ast.Import):
                modules = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = (node.module,)
            for module in modules:
                dependency = _IMPORT_DISTRIBUTIONS.get(module.partition(".")[0])
                if dependency is not None and dependency != owner:
                    imports.add(dependency)
    return imports


def test_engine_builds_and_runs_without_workspace_sources(tmp_path: Path) -> None:
    assert engine_isolation_findings(ROOT, tmp_path) == []


def test_legacy_declares_its_canonical_static_distribution_dependencies() -> None:
    manifest = json.loads(
        (ROOT / "docs/v0-package-classification.json").read_text(encoding="utf-8")
    )
    phase4 = manifest["phase4"]
    graph = phase4["runtime_dependency_graph"]
    version = phase4["release_identity"]["candidate_version"]
    metadata = tomllib.loads(
        (ROOT / "packages/legacy/pyproject.toml").read_text(encoding="utf-8")
    )
    expected = {f"{_PROJECT_NAMES[owner]}=={version}" for owner in graph["legacy"]}

    assert _static_distribution_imports(
        ROOT / "packages/legacy/src", owner="legacy"
    ) == set(graph["legacy"])
    assert set(metadata["project"]["dependencies"]) == expected


@pytest.mark.parametrize("distribution", ("legacy",))
def test_legacy_distribution_builds_private_artifacts_without_workspace_sources(
    tmp_path: Path,
    distribution: str,
) -> None:
    project = ROOT / "packages" / distribution
    metadata = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    output = tmp_path / distribution

    completed = subprocess.run(
        build_command(project, output),
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=1800,
    )

    assert metadata["tool"]["uv"]["package"] is False
    assert completed.returncode == 0, completed.stderr
    wheels = tuple(output.glob("open_brain_legacy-*.whl"))
    assert len(wheels) == 1
    assert len(tuple(output.glob("open_brain_legacy-*.tar.gz"))) == 1
    with zipfile.ZipFile(wheels[0]) as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith("/METADATA"))
        artifact_metadata = archive.read(metadata_name).decode("utf-8")
    assert "Requires-Dist: open-brain==0.1.0" in artifact_metadata
    assert "Requires-Dist: open-brain-connectors==0.1.0" in artifact_metadata
    assert "Requires-Dist: open-brain-engine==0.1.0" in artifact_metadata
