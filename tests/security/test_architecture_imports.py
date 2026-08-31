import ast
import json
from pathlib import Path
from typing import cast

REPOSITORY_ROOT = Path(__file__).parents[2]
CLASSIFICATION_PATH = REPOSITORY_ROOT / "docs" / "v0-package-classification.json"
SOURCE_ROOT = REPOSITORY_ROOT / "src" / "open_brain"


def _load_classification() -> dict[str, object]:
    value = json.loads(CLASSIFICATION_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("package classification must be an object")
    return cast(dict[str, object], value)


def _package_directories(source_root: Path) -> set[str]:
    return {
        path.name
        for path in source_root.iterdir()
        if path.is_dir() and path.name != "__pycache__"
    }


def _root_modules(source_root: Path) -> set[str]:
    return {path.stem for path in source_root.glob("*.py")}


def _source_files(source_root: Path) -> list[Path]:
    return sorted(path for path in source_root.rglob("*.py") if "__pycache__" not in path.parts)


def _source_namespace(path: Path, source_root: Path) -> str:
    relative = path.relative_to(source_root)
    return relative.parts[0] if len(relative.parts) > 1 else relative.stem


def _absolute_imports(path: Path, source_root: Path) -> list[tuple[int, str]]:
    relative = path.relative_to(source_root).with_suffix("")
    source_module = ".".join(("open_brain", *relative.parts))
    package = source_module.rpartition(".")[0]
    imports: list[tuple[int, str]] = []

    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
        if isinstance(node, ast.Import):
            imports.extend(
                (node.lineno, alias.name)
                for alias in node.names
                if alias.name.startswith("open_brain.")
            )
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package_parts = package.split(".")
                base = package_parts[: len(package_parts) - node.level + 1]
                module = ".".join((*base, *(node.module or "").split("."))).rstrip(".")
            else:
                module = node.module or ""
            if module == "open_brain":
                imports.extend((node.lineno, f"open_brain.{alias.name}") for alias in node.names)
            elif module.startswith("open_brain."):
                imports.append((node.lineno, module))

    return imports


def _current_namespace_imports(source_root: Path) -> list[tuple[str, int, str]]:
    imports: list[tuple[str, int, str]] = []
    for path in _source_files(source_root):
        imports.extend(
            (_source_namespace(path, source_root), line, imported_module)
            for line, imported_module in _absolute_imports(path, source_root)
        )
    return imports


def _dynamic_import_sites(source_root: Path) -> set[str]:
    sites: set[str] = set()
    for path in _source_files(source_root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            is_dynamic = (
                isinstance(function, ast.Name)
                and function.id in {"__import__", "import_module"}
            ) or (isinstance(function, ast.Attribute) and function.attr == "import_module")
            if is_dynamic:
                sites.add(path.relative_to(source_root).as_posix())
    return sites


def _files_for_namespace(source_root: Path, namespace: str) -> list[Path]:
    package = source_root / namespace
    if package.is_dir():
        return sorted(package.rglob("*.py"))
    module = source_root / f"{namespace}.py"
    return [module] if module.is_file() else []


def _architecture_violations(source_root: Path) -> list[str]:
    classification = _load_classification()
    packages = classification["packages"]
    root_modules = classification["root_modules"]
    root_public_symbols = classification["root_public_symbols"]
    rules = classification["rules"]
    assert isinstance(packages, dict)
    assert isinstance(root_modules, dict)
    assert isinstance(root_public_symbols, list)
    assert isinstance(rules, list)
    targets = packages | root_modules
    violations: list[str] = []

    for rule in rules:
        assert isinstance(rule, dict)
        rule_id = rule["id"]
        source_packages = rule["source_packages"]
        forbidden_classifications = rule["forbidden_classifications"]
        assert isinstance(rule_id, str)
        assert isinstance(source_packages, list)
        assert isinstance(forbidden_classifications, list)

        for source_package in source_packages:
            assert isinstance(source_package, str)
            for path in _files_for_namespace(source_root, source_package):
                for line, imported_module in _absolute_imports(path, source_root):
                    target_package = imported_module.split(".")[1]
                    if target_package in root_public_symbols:
                        target_package = "__init__"
                    target = targets[target_package]
                    assert isinstance(target, dict)
                    target_classification = target["classification"]
                    assert isinstance(target_classification, str)
                    if target_classification in forbidden_classifications:
                        violations.append(
                            f"{path.relative_to(source_root)}:{line}: {rule_id}: "
                            f"{source_package} cannot import {target_package} "
                            f"({target_classification})"
                        )

    return violations


def test_every_immediate_package_has_one_explicit_classification() -> None:
    classification = _load_classification()
    packages = classification["packages"]
    assert isinstance(packages, dict)
    assert set(packages) == _package_directories(SOURCE_ROOT)
    assert all(
        isinstance(package, dict)
        and all(
            isinstance(package.get(field), str)
            for field in ("classification", "target_owner", "current_scope", "phase_1_action")
        )
        for package in packages.values()
    )


def test_every_root_module_has_one_explicit_classification() -> None:
    classification = _load_classification()
    root_modules = classification["root_modules"]
    assert isinstance(root_modules, dict)
    assert set(root_modules) == _root_modules(SOURCE_ROOT)


def test_current_namespace_imports_have_classified_endpoints() -> None:
    classification = _load_classification()
    packages = classification["packages"]
    root_modules = classification["root_modules"]
    root_public_symbols = classification["root_public_symbols"]
    assert isinstance(packages, dict)
    assert isinstance(root_modules, dict)
    assert isinstance(root_public_symbols, list)
    imports = _current_namespace_imports(SOURCE_ROOT)
    assert imports
    assert {
        imported_module.split(".")[1]
        for _, _, imported_module in imports
        if imported_module.count(".") >= 1
    } <= set(packages) | set(root_modules) | set(root_public_symbols)


def test_dynamic_import_sites_are_explicitly_reviewed() -> None:
    classification = _load_classification()
    dynamic_sites = classification["dynamic_import_sites"]
    assert isinstance(dynamic_sites, list)
    expected = {
        item["path"]
        for item in dynamic_sites
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    assert expected == _dynamic_import_sites(SOURCE_ROOT)


def test_current_classified_graph_has_no_scoped_import_violations() -> None:
    assert _architecture_violations(SOURCE_ROOT) == []


def test_engine_to_interface_import_is_rejected(tmp_path: Path) -> None:
    synthetic_source_root = tmp_path / "src" / "open_brain"
    synthetic_core = synthetic_source_root / "core"
    synthetic_core.mkdir(parents=True)
    (synthetic_core / "forbidden.py").write_text("from open_brain.cli import main\n")

    assert _architecture_violations(synthetic_source_root) == [
        "core/forbidden.py:1: engine-to-interface: core cannot import cli (app)"
    ]


def test_engine_to_interface_alias_import_is_rejected(tmp_path: Path) -> None:
    synthetic_source_root = tmp_path / "src" / "open_brain"
    synthetic_core = synthetic_source_root / "core"
    synthetic_core.mkdir(parents=True)
    (synthetic_core / "forbidden.py").write_text(
        "from open_brain import cli\n", encoding="utf-8"
    )

    assert _architecture_violations(synthetic_source_root) == [
        "core/forbidden.py:1: engine-to-interface: core cannot import cli (app)"
    ]
