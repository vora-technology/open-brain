"""Bounded direct-Markdown reconciliation for canonical owner content."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from open_brain.portable.v1 import validate_portable_write
from open_brain.storage.filesystem import RootConfinementError, StorageError, read_confined_tree
from open_brain.storage.markdown import MarkdownFormatError, parse_markdown

from .contracts import ReconciliationReceipt

if TYPE_CHECKING:
    from .local import BrainEngine

_MAXIMUM_MARKDOWN_BYTES = 64 * 1024
_MAXIMUM_SCANNED_FILES = 256
_MAXIMUM_TOTAL_MARKDOWN_BYTES = _MAXIMUM_MARKDOWN_BYTES * _MAXIMUM_SCANNED_FILES


@dataclass(frozen=True, slots=True)
class _SpaceUpdate:
    space_id: str
    name: str


@dataclass(frozen=True, slots=True)
class _PageUpdate:
    page_id: str
    capture_id: str
    payload_family: str
    space_id: str
    title: str
    body: str
    trust: str
    updated_at: str
    canonical_path: str


class ReconciliationTasks:
    """Refresh derived retrieval state from owner-edited canonical Markdown bytes."""

    def __init__(self, engine: BrainEngine) -> None:
        self._engine = engine

    def reconcile(self) -> ReconciliationReceipt:
        self._engine._assert_root()
        with self._engine._writer_lease.acquire_shared_writer():
            scanned_files, space_updates, page_updates = self._scan()
            if not space_updates and not page_updates:
                return ReconciliationReceipt(
                    status="noop",
                    scanned_files=scanned_files,
                    page_updates=0,
                    space_updates=0,
                )
            with self._engine._store.transaction() as connection:
                for space_update in space_updates:
                    connection.execute(
                        "UPDATE spaces SET name = ? WHERE space_id = ?",
                        (space_update.name, space_update.space_id),
                    )
                for page_update in page_updates:
                    self._engine._upsert_canonical_search(
                        connection,
                        result_id=page_update.page_id,
                        capture_id=page_update.capture_id,
                        payload_family=page_update.payload_family,
                        space_id=page_update.space_id,
                        title=page_update.title,
                        body=page_update.body,
                        trust=page_update.trust,
                        canonical_path=page_update.canonical_path,
                        updated_at=page_update.updated_at,
                    )
            return ReconciliationReceipt(
                status="reconciled",
                scanned_files=scanned_files,
                page_updates=len(page_updates),
                space_updates=len(space_updates),
            )

    def _scan(self) -> tuple[int, tuple[_SpaceUpdate, ...], tuple[_PageUpdate, ...]]:
        connection = self._engine._store.connect()
        try:
            known_spaces = {
                cast(str, row["space_id"]): (cast(str, row["name"]), cast(str, row["slug"]))
                for row in connection.execute("SELECT space_id, name, slug FROM spaces")
            }
            canonical_rows = {
                cast(str, row["canonical_path"]): row
                for row in connection.execute(
                    """
                    SELECT result_id, capture_id, payload_family, space_id, title, body, trust,
                           updated_at, canonical_path
                    FROM search_documents
                    WHERE record_type = 'canonical'
                    """
                )
            }
        finally:
            connection.close()
        try:
            files = read_confined_tree(
                root=self._engine.profile.root,
                relative="content/spaces",
                expected_root_identity=self._engine.profile.root_identity,
                maximum_entries=_MAXIMUM_SCANNED_FILES,
                maximum_file_bytes=_MAXIMUM_MARKDOWN_BYTES,
                maximum_total_bytes=_MAXIMUM_TOTAL_MARKDOWN_BYTES,
            )
        except RootConfinementError as error:
            raise ValueError("canonical Markdown symlink or unsafe path is not allowed") from error
        except StorageError as error:
            raise ValueError("canonical Markdown exceeds the bounded size or file count") from error
        space_updates: list[_SpaceUpdate] = []
        page_updates: list[_PageUpdate] = []
        seen_spaces: set[str] = set()
        seen_pages: set[str] = set()
        for relative, payload in files:
            parts = relative.parts
            canonical_path = f"content/spaces/{relative.as_posix()}"
            fields = _parse(payload)
            _require_owner_identity(fields, self._engine)
            try:
                validate_portable_write(
                    canonical_path,
                    payload,
                    self._engine.profile.tenant_id,
                )
            except ValueError as error:
                raise ValueError("canonical Markdown is invalid") from error
            if len(parts) == 2 and parts[1] == "_space.md":
                slug = parts[0]
                space_id = _required_string(fields, "space_id")
                expected = known_spaces.get(space_id)
                if expected is None:
                    raise ValueError("canonical space identity is unknown")
                if _required_string(fields, "slug") != slug or expected[1] != slug:
                    raise ValueError("canonical space slug changed")
                seen_spaces.add(space_id)
                name = _required_string(fields, "name")
                if name != expected[0]:
                    space_updates.append(_SpaceUpdate(space_id=space_id, name=name))
                continue
            if len(parts) != 3 or parts[1] != "notes":
                raise ValueError("canonical Markdown inventory is invalid")
            page_id = _required_string(fields, "page_id")
            if parts[2] != f"{page_id}.md":
                raise ValueError("canonical page identity changed")
            row = canonical_rows.get(canonical_path)
            if row is None or cast(str, row["result_id"]) != page_id:
                raise ValueError("canonical page provenance changed")
            space_id = _required_string(fields, "space_id")
            capture_id = cast(str, row["capture_id"])
            provenance = fields.get("provenance")
            if (
                space_id != cast(str, row["space_id"])
                or space_id not in seen_spaces
                or provenance != [capture_id]
            ):
                raise ValueError("canonical page provenance changed")
            seen_pages.add(canonical_path)
            parsed = parse_markdown(payload)
            title = _required_string(fields, "title")
            trust = _required_string(fields, "trust")
            updated_at = _required_string(fields, "modified_at")
            if (
                title != cast(str, row["title"])
                or parsed.body != cast(str, row["body"])
                or trust != cast(str, row["trust"])
                or updated_at != cast(str, row["updated_at"])
            ):
                page_updates.append(
                    _PageUpdate(
                        page_id=page_id,
                        capture_id=capture_id,
                        payload_family=cast(str, row["payload_family"]),
                        space_id=space_id,
                        title=title,
                        body=parsed.body,
                        trust=trust,
                        updated_at=updated_at,
                        canonical_path=canonical_path,
                    )
                )
        if seen_spaces != set(known_spaces):
            raise ValueError("canonical space Markdown is missing")
        missing_pages = set(canonical_rows) - seen_pages
        if missing_pages:
            raise ValueError("canonical page Markdown is missing")
        return len(files), tuple(space_updates), tuple(page_updates)


def _parse(payload: bytes) -> dict[str, object]:
    try:
        return dict(parse_markdown(payload).fields)
    except MarkdownFormatError as error:
        raise ValueError("canonical Markdown is invalid") from error


def _required_string(fields: dict[str, object], key: str) -> str:
    value = fields.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError("canonical Markdown is invalid")
    return value


def _require_owner_identity(fields: dict[str, object], engine: BrainEngine) -> None:
    role_claim = fields.get("role_claim")
    expected = engine.profile.owner_role_claim
    capabilities = role_claim.get("capabilities") if isinstance(role_claim, Mapping) else None
    expected_capabilities = expected.get("capabilities")
    if (
        _required_string(fields, "tenant_id") != engine.profile.tenant_id
        or _required_string(fields, "actor_id") != engine.profile.owner_actor_id
        or not isinstance(role_claim, Mapping)
        or any(
            role_claim.get(key) != expected.get(key)
            for key in ("actor_id", "role_claim_id", "role_id", "tenant_id")
        )
        or not isinstance(capabilities, (list, tuple))
        or not isinstance(expected_capabilities, (list, tuple))
        or tuple(capabilities) != tuple(expected_capabilities)
    ):
        raise ValueError("canonical Markdown owner identity changed")
