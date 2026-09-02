"""Rewrite runtime imports deterministically from the canonical Phase 4 manifest."""

from __future__ import annotations

import argparse
import ast
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, cast

from tools.phase4.move_manifest import MANIFEST_RELATIVE, load_manifest


class _PositionedNode(Protocol):
    end_lineno: int
    end_col_offset: int


def import_rewrites(manifest: Mapping[str, object]) -> dict[str, str]:
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("manifest runtime files are missing")
    rewrites: dict[str, str] = {}
    for value in files.values():
        if not isinstance(value, dict):
            raise ValueError("manifest runtime record is malformed")
        rewrite = value.get("import_rewrite")
        if not isinstance(rewrite, dict):
            raise ValueError("manifest runtime import rewrite is missing")
        source = rewrite.get("from")
        target = rewrite.get("to")
        if not isinstance(source, str) or not isinstance(target, str):
            raise ValueError("manifest runtime import rewrite is malformed")
        active = target if value.get("movement_state") == "moved" else source
        for alias in (source, target):
            previous = rewrites.setdefault(alias, active)
            if previous != active:
                raise ValueError(f"conflicting import rewrite alias: {alias}")
    return rewrites


def rewrite_text(source: str, rewrites: Mapping[str, str]) -> str:
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def offset(position: tuple[int, int]) -> int:
        line, column = position
        return offsets[line - 1] + column

    def end_position(node: ast.AST) -> tuple[int, int]:
        positioned = cast(_PositionedNode, node)
        return positioned.end_lineno, positioned.end_col_offset

    replacements: list[tuple[int, int, str]] = []
    tree = ast.parse(source)
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    qualified_roots: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            segment = ast.get_source_segment(source, node)
            if segment is None:
                continue
            rewritten = segment
            for alias in sorted(node.names, key=lambda value: -len(value.name)):
                active = _active_module(alias.name, rewrites)
                if active == alias.name:
                    continue
                rewritten = re.sub(
                    rf"(?<![A-Za-z0-9_]){re.escape(alias.name)}(?![A-Za-z0-9_])",
                    active,
                    rewritten,
                    count=1,
                )
                if alias.asname is None:
                    qualified_roots[alias.name.split(".")[0]] = active.split(".")[0]
            if rewritten != segment:
                replacements.append(
                    (
                        offset((node.lineno, node.col_offset)),
                        offset(end_position(node)),
                        rewritten,
                    )
                )
            continue
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            destinations: set[str] = set()
            active_module = _active_module(node.module, rewrites)
            for alias in node.names:
                candidate = f"{node.module}.{alias.name}"
                active_candidate = rewrites.get(candidate)
                destinations.add(
                    active_candidate.rpartition(".")[0]
                    if active_candidate is not None
                    else active_module
                )
            if len(destinations) != 1:
                raise ValueError(f"split import-from destinations: {node.module}")
            destination = destinations.pop()
            if destination != node.module:
                segment = ast.get_source_segment(source, node)
                if segment is not None:
                    rewritten = re.sub(
                        rf"^(from\s+){re.escape(node.module)}(\s+import\b)",
                        rf"\1{destination}\2",
                        segment,
                        count=1,
                    )
                    replacements.append(
                        (
                            offset((node.lineno, node.col_offset)),
                            offset(end_position(node)),
                            rewritten,
                        )
                    )
            continue
        if isinstance(node, ast.Attribute) and not isinstance(parents.get(node), ast.Attribute):
            segment = ast.get_source_segment(source, node)
            if segment is None or segment.split(".", 1)[0] not in qualified_roots:
                continue
            active = _active_module(segment, rewrites)
            if active != segment:
                replacements.append(
                    (
                        offset((node.lineno, node.col_offset)),
                        offset(end_position(node)),
                        active,
                    )
                )
            continue
        if not isinstance(node, ast.Call) or not node.args:
            continue
        function = node.func
        dynamic = (
            isinstance(function, ast.Name)
            and function.id in {"__import__", "import_module"}
        ) or (isinstance(function, ast.Attribute) and function.attr == "import_module")
        patch_target = (
            isinstance(function, ast.Name) and function.id in {"patch", "setattr"}
        ) or (isinstance(function, ast.Attribute) and function.attr in {"patch", "setattr"})
        argument = node.args[0]
        if (
            not (dynamic or patch_target)
            or not isinstance(argument, ast.Constant)
            or not isinstance(argument.value, str)
        ):
            continue
        active = _active_module(argument.value, rewrites)
        if active != argument.value and hasattr(argument, "end_lineno"):
            replacements.append(
                (
                    offset((argument.lineno, argument.col_offset)),
                    offset((cast(int, argument.end_lineno), cast(int, argument.end_col_offset))),
                    repr(active),
                )
            )

    rewritten = source
    for start, end_offset, replacement in sorted(replacements, reverse=True):
        rewritten = rewritten[:start] + replacement + rewritten[end_offset:]
    return rewritten


def _active_module(module: str, rewrites: Mapping[str, str]) -> str:
    for alias in sorted(rewrites, key=lambda value: (-len(value), value)):
        if module == alias or module.startswith(f"{alias}."):
            return f"{rewrites[alias]}{module[len(alias):]}"
    return module


def rewrite_relative_imports(
    source: str,
    *,
    source_module: str,
    source_is_package: bool,
    source_moved: bool,
    rewrites: Mapping[str, str],
) -> str:
    """Make only cross-distribution relative imports absolute during a wave."""

    if source_moved:
        return source
    package = source_module if source_is_package else source_module.rpartition(".")[0]
    package_parts = package.split(".")
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.level == 0:
            continue
        keep = len(package_parts) - node.level + 1
        if keep < 1:
            continue
        parts = package_parts[:keep]
        if node.module:
            parts.extend(node.module.split("."))
        absolute = ".".join(parts)
        active = _active_module(absolute, rewrites)
        if active == absolute:
            continue
        line_index = node.lineno - 1
        lines[line_index] = re.sub(
            r"^(\s*)from\s+\.+[A-Za-z0-9_.]*\s+import\b",
            rf"\1from {active} import",
            lines[line_index],
            count=1,
        )
    return "".join(lines)


def active_python_paths(root: Path, manifest: Mapping[str, object]) -> tuple[Path, ...]:
    files = cast(dict[str, object], manifest["files"])
    phase4 = cast(dict[str, object], manifest["phase4"])
    subjects = cast(dict[str, object], phase4["subjects"])
    paths: set[Path] = set()
    for value in [*files.values(), *subjects.values()]:
        if not isinstance(value, dict):
            continue
        if value.get("kind", "runtime") not in {"runtime", "test"}:
            continue
        current = value.get("current_path")
        target = value.get("target_path")
        if not isinstance(current, str) or not isinstance(target, str):
            continue
        current_path = root / current
        target_path = root / target
        active = (
            target_path
            if target_path.is_file() and not current_path.is_file()
            else current_path
        )
        if active.suffix == ".py" and active.is_file():
            paths.add(active)
    return tuple(sorted(paths))


def rewrite_repository(root: Path, *, write: bool) -> tuple[str, ...]:
    manifest = load_manifest(root / MANIFEST_RELATIVE)
    rewrites = import_rewrites(manifest)
    runtime = cast(dict[str, object], manifest["files"])
    active_records: dict[Path, dict[str, object]] = {}
    for value in runtime.values():
        if not isinstance(value, dict):
            continue
        current = value.get("current_path")
        target = value.get("target_path")
        if not isinstance(current, str) or not isinstance(target, str):
            continue
        current_path = root / current
        target_path = root / target
        active = (
            target_path
            if target_path.is_file() and not current_path.is_file()
            else current_path
        )
        active_records[active] = cast(dict[str, object], value)
    changed: list[str] = []
    for path in active_python_paths(root, manifest):
        source = path.read_text(encoding="utf-8")
        rewritten = rewrite_text(source, rewrites)
        record = active_records.get(path)
        if record is not None:
            rewrite = cast(dict[str, object], record["import_rewrite"])
            source_module = cast(str, rewrite["from"])
            rewritten = rewrite_relative_imports(
                rewritten,
                source_module=source_module,
                source_is_package=cast(str, record["current_path"]).endswith("/__init__.py")
                or cast(str, record["current_path"]).endswith("src/open_brain/__init__.py"),
                source_moved=record.get("movement_state") == "moved",
                rewrites=rewrites,
            )
        if rewritten == source:
            continue
        changed.append(path.relative_to(root).as_posix())
        if write:
            path.write_text(rewritten, encoding="utf-8")
    return tuple(changed)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("check", "rewrite"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    changed = rewrite_repository(args.root.resolve(), write=args.command == "rewrite")
    for path in changed:
        print(path)
    return 1 if args.command == "check" and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
