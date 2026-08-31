import ast
import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

REPOSITORY_ROOT = Path(__file__).parents[2]
CLASSIFICATION_PATH = REPOSITORY_ROOT / "docs" / "v0-package-classification.json"
SOURCE_ROOT = REPOSITORY_ROOT / "src" / "open_brain"
OWNERS = {"engine", "app", "connector", "hosted", "legacy", "workspace"}


@dataclass(frozen=True, slots=True)
class ImportReference:
    line: int
    module: str


@dataclass(frozen=True, slots=True)
class DynamicImportSite:
    path: str
    line: int


def _load_classification() -> dict[str, object]:
    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate classification key: {key}")
            value[key] = item
        return value

    value = json.loads(
        CLASSIFICATION_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=unique_object,
    )
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


def _classified_files(classification: dict[str, object]) -> dict[str, object]:
    files = classification.get("files")
    if not isinstance(files, dict):
        raise TypeError("classification files must be an object")
    return cast(dict[str, object], files)


def _metadata(files: dict[str, object], relative_path: str) -> dict[str, object]:
    value = files[relative_path]
    if not isinstance(value, dict):
        raise TypeError(f"file classification must be an object: {relative_path}")
    return cast(dict[str, object], value)


def _module_for_path(path: Path, source_root: Path) -> str:
    relative = path.relative_to(source_root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(("open_brain", *parts))


def _package_for_path(path: Path, source_root: Path) -> str:
    module = _module_for_path(path, source_root)
    if path.name == "__init__.py":
        return module
    return module.rpartition(".")[0]


def _absolute_from_module(node: ast.ImportFrom, path: Path, source_root: Path) -> str:
    if node.level == 0:
        return node.module or ""
    package_parts = _package_for_path(path, source_root).split(".")
    keep = len(package_parts) - node.level + 1
    if keep < 1:
        return ""
    base = package_parts[:keep]
    if node.module:
        base.extend(node.module.split("."))
    return ".".join(base)


def _module_target(module: str, classified_paths: set[str]) -> str | None:
    if module == "open_brain":
        return "__init__.py" if "__init__.py" in classified_paths else None
    if not module.startswith("open_brain."):
        return None
    relative = module.removeprefix("open_brain.").replace(".", "/")
    module_path = f"{relative}.py"
    package_path = f"{relative}/__init__.py"
    if module_path in classified_paths:
        return module_path
    if package_path in classified_paths:
        return package_path
    return None


def _is_dynamic_import_call(node: ast.Call) -> bool:
    function = node.func
    return (
        isinstance(function, ast.Name)
        and function.id in {"__import__", "import_module"}
    ) or (isinstance(function, ast.Attribute) and function.attr == "import_module")


def _import_references(
    path: Path,
    source_root: Path,
    classified_paths: set[str],
) -> list[ImportReference]:
    references: list[ImportReference] = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            references.extend(
                ImportReference(node.lineno, alias.name)
                for alias in node.names
                if alias.name == "open_brain" or alias.name.startswith("open_brain.")
            )
        elif isinstance(node, ast.ImportFrom):
            module = _absolute_from_module(node, path, source_root)
            if module != "open_brain" and not module.startswith("open_brain."):
                continue
            for alias in node.names:
                candidate = module if alias.name == "*" else f"{module}.{alias.name}"
                target_module = (
                    candidate
                    if _module_target(candidate, classified_paths) is not None
                    else module
                )
                references.append(ImportReference(node.lineno, target_module))
        elif isinstance(node, ast.Call) and _is_dynamic_import_call(node) and node.args:
            argument = node.args[0]
            if (
                isinstance(argument, ast.Constant)
                and isinstance(argument.value, str)
                and (
                    argument.value == "open_brain"
                    or argument.value.startswith("open_brain.")
                )
            ):
                references.append(ImportReference(node.lineno, argument.value))
    return references


def _nonliteral_dynamic_import_sites(source_root: Path) -> list[DynamicImportSite]:
    sites: set[DynamicImportSite] = set()
    for path in _source_files(source_root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _is_dynamic_import_call(node):
                continue
            argument = node.args[0] if node.args else None
            if not (
                isinstance(argument, ast.Constant) and isinstance(argument.value, str)
            ):
                sites.add(
                    DynamicImportSite(path.relative_to(source_root).as_posix(), node.lineno)
                )
    return sorted(sites, key=lambda site: (site.path, site.line))


def _selector_matches(metadata: dict[str, object], selector: object) -> bool:
    if not isinstance(selector, dict):
        raise TypeError("rule selector must be an object")
    owners = selector.get("owners")
    apis = selector.get("apis")
    roles_any = selector.get("roles_any")
    roles_none = selector.get("roles_none")
    roles = metadata.get("roles")
    if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
        raise TypeError("file roles must be a string list")
    if owners is not None and metadata.get("owner") not in owners:
        return False
    if apis is not None and metadata.get("api") not in apis:
        return False
    if roles_any is not None and not set(roles).intersection(roles_any):
        return False
    return roles_none is None or not set(roles).intersection(roles_none)


def _relation_matches(
    source: dict[str, object],
    target: dict[str, object],
    relation: object,
) -> bool:
    if relation is None:
        return True
    if relation != "different-adapter-group":
        raise ValueError(f"unsupported architecture relation: {relation}")
    source_group = source.get("adapter_group")
    target_group = target.get("adapter_group")
    return (
        isinstance(source_group, str)
        and isinstance(target_group, str)
        and source_group != target_group
    )


def _architecture_violations(
    source_root: Path,
    *,
    classification: dict[str, object] | None = None,
) -> list[str]:
    active = _load_classification() if classification is None else classification
    files = _classified_files(active)
    classified_paths = set(files)
    rules = active.get("rules")
    if not isinstance(rules, list):
        raise TypeError("architecture rules must be a list")
    violations: set[str] = set()

    for path in _source_files(source_root):
        source_path = path.relative_to(source_root).as_posix()
        source = _metadata(files, source_path)
        references = _import_references(path, source_root, classified_paths)
        for reference in references:
            target_path = _module_target(reference.module, classified_paths)
            if target_path is None:
                continue
            target = _metadata(files, target_path)
            for rule in rules:
                if not isinstance(rule, dict):
                    raise TypeError("architecture rule must be an object")
                rule_id = rule.get("id")
                clauses = rule.get("violations")
                if not isinstance(rule_id, str) or not isinstance(clauses, list):
                    raise TypeError("architecture rule is malformed")
                if not _selector_matches(source, rule.get("source")):
                    continue
                for clause in clauses:
                    if not isinstance(clause, dict):
                        raise TypeError("architecture violation clause must be an object")
                    if _selector_matches(target, clause.get("target")) and _relation_matches(
                        source,
                        target,
                        clause.get("relation"),
                    ):
                        violations.add(
                            f"{rule_id}: {source_path}:{reference.line} -> {target_path}"
                        )
                        break
    return sorted(violations)


def _ownership_errors(
    source_root: Path,
    classification: dict[str, object],
) -> list[str]:
    files = _classified_files(classification)
    discovered = {
        path.relative_to(source_root).as_posix() for path in _source_files(source_root)
    }
    classified = set(files)
    errors = [f"unclassified runtime file: {path}" for path in discovered - classified]
    errors.extend(f"stale file classification: {path}" for path in classified - discovered)
    for relative_path in discovered & classified:
        metadata = _metadata(files, relative_path)
        owner = metadata.get("owner")
        api = metadata.get("api")
        roles = metadata.get("roles")
        if owner not in OWNERS:
            errors.append(f"invalid owner for {relative_path}: {owner}")
        if api not in {"public", "internal"}:
            errors.append(f"invalid api classification for {relative_path}: {api}")
        if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
            errors.append(f"invalid roles for {relative_path}")
        elif roles != sorted(set(roles)):
            errors.append(f"roles must be sorted and unique for {relative_path}")
        if isinstance(roles, list) and "adapter" in roles:
            if not isinstance(metadata.get("adapter_group"), str):
                errors.append(f"adapter group required for {relative_path}")
        elif "adapter_group" in metadata:
            errors.append(f"adapter group without adapter role for {relative_path}")
    return sorted(errors)


def _unresolved_internal_imports(
    source_root: Path,
    classification: dict[str, object],
) -> list[str]:
    files = _classified_files(classification)
    classified_paths = set(files)
    unresolved: set[str] = set()
    for path in _source_files(source_root):
        source_path = path.relative_to(source_root).as_posix()
        for reference in _import_references(path, source_root, classified_paths):
            if _module_target(reference.module, classified_paths) is None:
                unresolved.add(f"{source_path}:{reference.line} -> {reference.module}")
    return sorted(unresolved)


def _dynamic_import_review_errors(
    source_root: Path,
    classification: dict[str, object],
) -> list[str]:
    files = _classified_files(classification)
    sites = {(site.path, site.line) for site in _nonliteral_dynamic_import_sites(source_root)}
    reviews = classification.get("dynamic_import_reviews")
    if not isinstance(reviews, list):
        raise TypeError("dynamic import reviews must be a list")
    reviewed: set[tuple[str, int]] = set()
    errors: list[str] = []
    for review in reviews:
        if not isinstance(review, dict):
            raise TypeError("dynamic import review must be an object")
        path = review.get("path")
        line = review.get("line")
        owner = review.get("owner")
        allowed_host = review.get("allowed_host")
        rationale = review.get("rationale")
        if (
            not isinstance(path, str)
            or not isinstance(line, int)
            or not isinstance(owner, str)
            or not isinstance(allowed_host, bool)
            or not isinstance(rationale, str)
            or not rationale.strip()
        ):
            raise TypeError("dynamic import review is malformed")
        key = (path, line)
        if key in reviewed:
            errors.append(f"duplicate nonliteral dynamic import review: {path}:{line}")
            continue
        reviewed.add(key)
        if key not in sites:
            errors.append(f"stale nonliteral dynamic import review: {path}:{line}")
            continue
        metadata = _metadata(files, path)
        actual_owner = metadata.get("owner")
        roles = metadata.get("roles")
        actual_allowed = actual_owner == "app" and isinstance(roles, list) and (
            "extension_host" in roles
        )
        if owner != actual_owner:
            errors.append(f"dynamic import review owner mismatch: {path}:{line}")
        if allowed_host != actual_allowed:
            errors.append(f"dynamic import review host mismatch: {path}:{line}")
    errors.extend(
        f"unreviewed nonliteral dynamic import: {path}:{line}"
        for path, line in sites - reviewed
    )
    return sorted(errors)


def _nonliteral_dynamic_import_violations(
    source_root: Path,
    classification: dict[str, object],
) -> list[str]:
    files = _classified_files(classification)
    violations: list[str] = []
    for site in _nonliteral_dynamic_import_sites(source_root):
        metadata = _metadata(files, site.path)
        roles = metadata.get("roles")
        if metadata.get("owner") != "app" or not isinstance(roles, list) or (
            "extension_host" not in roles
        ):
            violations.append(f"nonliteral-dynamic-import: {site.path}:{site.line}")
    return violations


def _live_debt(
    source_root: Path,
    classification: dict[str, object],
) -> list[str]:
    return sorted(
        set(
            _architecture_violations(source_root, classification=classification)
            + _nonliteral_dynamic_import_violations(source_root, classification)
        )
    )


def _live_debt_errors(
    source_root: Path,
    classification: dict[str, object],
) -> list[str]:
    declared = classification.get("temporary_live_debt")
    if not isinstance(declared, list) or not all(isinstance(item, str) for item in declared):
        raise TypeError("temporary live debt must be a string list")
    errors: list[str] = []
    if declared != sorted(set(declared)):
        errors.append("temporary live debt must be sorted and unique")
    observed = set(_live_debt(source_root, classification))
    expected = set(declared)
    errors.extend(f"missing temporary debt: {item}" for item in observed - expected)
    errors.extend(f"stale temporary debt: {item}" for item in expected - observed)
    return sorted(errors)


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


def test_every_runtime_file_has_one_authoritative_owner() -> None:
    classification = _load_classification()
    assert _ownership_errors(SOURCE_ROOT, classification) == []


def test_current_namespace_imports_have_classified_file_endpoints() -> None:
    classification = _load_classification()
    classified_paths = set(_classified_files(classification))
    references = [
        reference
        for path in _source_files(SOURCE_ROOT)
        for reference in _import_references(path, SOURCE_ROOT, classified_paths)
    ]
    assert references
    assert _unresolved_internal_imports(SOURCE_ROOT, classification) == []


def test_nonliteral_dynamic_import_sites_are_explicitly_reviewed() -> None:
    classification = _load_classification()
    assert _dynamic_import_review_errors(SOURCE_ROOT, classification) == []


def test_current_import_violations_exactly_match_temporary_live_debt() -> None:
    classification = _load_classification()
    assert _live_debt_errors(SOURCE_ROOT, classification) == []


SYNTHETIC_FILES: dict[str, dict[str, object]] = {
    "app/composition.py": {
        "owner": "app",
        "api": "internal",
        "roles": ["composition"],
    },
    "app/extension_host.py": {
        "owner": "app",
        "api": "internal",
        "roles": ["extension_host"],
    },
    "app/representation.py": {
        "owner": "app",
        "api": "internal",
        "roles": ["representation"],
    },
    "connector_alpha/adapter.py": {
        "owner": "connector",
        "api": "internal",
        "roles": ["adapter"],
        "adapter_group": "alpha",
    },
    "connector_beta/adapter.py": {
        "owner": "connector",
        "api": "internal",
        "roles": ["adapter"],
        "adapter_group": "beta",
    },
    "engine/extension_contract.py": {
        "owner": "engine",
        "api": "internal",
        "roles": ["extension_contract"],
    },
    "engine/internal.py": {"owner": "engine", "api": "internal", "roles": []},
    "engine/public.py": {"owner": "engine", "api": "public", "roles": []},
    "engine/store.py": {
        "owner": "engine",
        "api": "internal",
        "roles": ["store"],
    },
    "hosted/service.py": {"owner": "hosted", "api": "internal", "roles": []},
    "legacy/migrate.py": {"owner": "legacy", "api": "internal", "roles": []},
    "workspace/tool.py": {"owner": "workspace", "api": "internal", "roles": []},
}


def _synthetic_classification() -> dict[str, object]:
    classification = _load_classification()
    return {
        **classification,
        "files": SYNTHETIC_FILES,
        "dynamic_import_reviews": [],
        "temporary_live_debt": [],
    }


def _write_synthetic_tree(source_root: Path, source_path: str, statement: str) -> None:
    for relative_path in SYNTHETIC_FILES:
        path = source_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(statement if relative_path == source_path else "", encoding="utf-8")


RULE_CASES = (
    ("engine-to-app", "engine/internal.py", "app/composition.py"),
    ("app-to-engine-internals", "app/composition.py", "engine/internal.py"),
    (
        "connector-capability-only",
        "connector_alpha/adapter.py",
        "engine/internal.py",
    ),
    ("shipping-to-legacy", "app/composition.py", "legacy/migrate.py"),
    ("hosted-to-local-internals", "hosted/service.py", "engine/internal.py"),
    ("representation-to-adapters", "app/representation.py", "engine/store.py"),
    (
        "adapter-to-adapter",
        "connector_alpha/adapter.py",
        "connector_beta/adapter.py",
    ),
    (
        "adapter-to-adapter",
        "connector_beta/adapter.py",
        "connector_alpha/adapter.py",
    ),
    ("runtime-to-workspace", "engine/internal.py", "workspace/tool.py"),
)

EXPECTED_RULE_IDS = (
    "engine-to-app",
    "app-to-engine-internals",
    "connector-capability-only",
    "shipping-to-legacy",
    "hosted-to-local-internals",
    "representation-to-adapters",
    "adapter-to-adapter",
    "runtime-to-workspace",
)


def _import_statement(form: str, target_path: str) -> str:
    module = f"open_brain.{target_path.removesuffix('.py').replace('/', '.')}"
    package, _, name = module.rpartition(".")
    if form == "import":
        return f"import {module}\n"
    if form == "from":
        return f"from {package} import {name}\n"
    if form == "import_module":
        return f'import importlib; importlib.import_module("{module}")\n'
    if form == "dunder_import":
        return f'__import__("{module}")\n'
    raise AssertionError(f"unsupported import form: {form}")


@pytest.mark.parametrize(("rule_id", "source_path", "target_path"), RULE_CASES)
@pytest.mark.parametrize("form", ("import", "from", "import_module", "dunder_import"))
def test_each_import_rule_rejects_static_and_literal_dynamic_forms(
    tmp_path: Path,
    rule_id: str,
    source_path: str,
    target_path: str,
    form: str,
) -> None:
    source_root = tmp_path / "open_brain"
    _write_synthetic_tree(source_root, source_path, _import_statement(form, target_path))

    violations = _architecture_violations(
        source_root,
        classification=_synthetic_classification(),
    )

    assert f"{rule_id}: {source_path}:1 -> {target_path}" in violations


def test_direct_literal_import_module_is_checked(tmp_path: Path) -> None:
    source_root = tmp_path / "open_brain"
    statement = (
        "from importlib import import_module; "
        'import_module("open_brain.app.composition")\n'
    )
    _write_synthetic_tree(source_root, "engine/internal.py", statement)

    assert (
        "engine-to-app: engine/internal.py:1 -> app/composition.py"
        in _architecture_violations(
            source_root,
            classification=_synthetic_classification(),
        )
    )


def test_all_eight_rules_are_machine_readable() -> None:
    rules = _load_classification()["rules"]
    assert isinstance(rules, list)
    assert tuple(rule["id"] for rule in rules if isinstance(rule, dict)) == EXPECTED_RULE_IDS


def test_synthetic_owner_coverage_rejects_missing_and_stale_files(tmp_path: Path) -> None:
    source_root = tmp_path / "open_brain"
    _write_synthetic_tree(source_root, "engine/internal.py", "")
    missing = deepcopy(_synthetic_classification())
    missing_files = cast(dict[str, object], missing["files"])
    del missing_files["engine/internal.py"]
    stale = deepcopy(_synthetic_classification())
    stale_files = cast(dict[str, object], stale["files"])
    stale_files["engine/removed.py"] = {
        "owner": "engine",
        "api": "internal",
        "roles": [],
    }

    assert _ownership_errors(source_root, missing) == [
        "unclassified runtime file: engine/internal.py"
    ]
    assert _ownership_errors(source_root, stale) == [
        "stale file classification: engine/removed.py"
    ]


def test_synthetic_live_debt_rejects_missing_and_stale_edges(tmp_path: Path) -> None:
    source_root = tmp_path / "open_brain"
    statement = "import open_brain.app.composition\n"
    _write_synthetic_tree(source_root, "engine/internal.py", statement)
    missing = _synthetic_classification()
    stale = deepcopy(missing)
    stale["temporary_live_debt"] = [
        "engine-to-app: engine/internal.py:1 -> app/composition.py",
        "engine-to-app: engine/internal.py:99 -> app/composition.py",
    ]

    assert _live_debt_errors(source_root, missing) == [
        "missing temporary debt: engine-to-app: engine/internal.py:1 -> app/composition.py"
    ]
    assert _live_debt_errors(source_root, stale) == [
        "stale temporary debt: engine-to-app: engine/internal.py:99 -> app/composition.py"
    ]


def test_reviewed_app_extension_host_nonliteral_import_is_allowed(tmp_path: Path) -> None:
    source_root = tmp_path / "open_brain"
    statement = (
        "from importlib import import_module\n"
        'module_name = "open_brain.engine.public"\n'
        "import_module(module_name)\n"
    )
    _write_synthetic_tree(source_root, "app/extension_host.py", statement)
    classification = _synthetic_classification()
    classification["dynamic_import_reviews"] = [
        {
            "path": "app/extension_host.py",
            "line": 3,
            "owner": "app",
            "allowed_host": True,
            "rationale": "Loads a named synthetic extension after allow-list validation.",
        }
    ]

    assert _dynamic_import_review_errors(source_root, classification) == []
    assert _nonliteral_dynamic_import_violations(source_root, classification) == []


def test_arbitrary_reviewed_nonliteral_import_is_temporary_debt(tmp_path: Path) -> None:
    source_root = tmp_path / "open_brain"
    statement = (
        "from importlib import import_module\n"
        'module_name = "open_brain.app.composition"\n'
        "import_module(module_name)\n"
    )
    _write_synthetic_tree(source_root, "engine/internal.py", statement)
    classification = _synthetic_classification()
    classification["dynamic_import_reviews"] = [
        {
            "path": "engine/internal.py",
            "line": 3,
            "owner": "engine",
            "allowed_host": False,
            "rationale": "Synthetic temporary debt outside the app extension host.",
        }
    ]

    assert _dynamic_import_review_errors(source_root, classification) == []
    assert _nonliteral_dynamic_import_violations(source_root, classification) == [
        "nonliteral-dynamic-import: engine/internal.py:3"
    ]


def test_nonliteral_import_review_inventory_is_exact(tmp_path: Path) -> None:
    source_root = tmp_path / "open_brain"
    statement = "from importlib import import_module\nimport_module(module_name)\n"
    _write_synthetic_tree(source_root, "app/extension_host.py", statement)
    missing = _synthetic_classification()
    stale = deepcopy(missing)
    stale["dynamic_import_reviews"] = [
        {
            "path": "app/extension_host.py",
            "line": 99,
            "owner": "app",
            "allowed_host": True,
            "rationale": "Stale synthetic review.",
        }
    ]

    assert _dynamic_import_review_errors(source_root, missing) == [
        "unreviewed nonliteral dynamic import: app/extension_host.py:2"
    ]
    assert _dynamic_import_review_errors(source_root, stale) == [
        "stale nonliteral dynamic import review: app/extension_host.py:99",
        "unreviewed nonliteral dynamic import: app/extension_host.py:2",
    ]


def test_literal_external_dynamic_import_needs_no_internal_review(tmp_path: Path) -> None:
    source_root = tmp_path / "open_brain"
    statement = 'import importlib\nimportlib.import_module("external_sdk")\n'
    _write_synthetic_tree(source_root, "connector_alpha/adapter.py", statement)
    classification = _synthetic_classification()

    assert _dynamic_import_review_errors(source_root, classification) == []
    assert _architecture_violations(source_root, classification=classification) == []
