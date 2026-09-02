from __future__ import annotations

from pathlib import Path

from open_brain_engine.engine import (
    CaptureAction,
    TextPayload,
    acquire_daemon_authority,
    open_authoritative_local_engine,
    open_local_engine,
)
from open_brain_engine.storage.markdown import parse_markdown, render_markdown

from open_brain.profile import compile_single_user_local, open_existing_single_user_local


def test_reconciliation_updates_retrieval_and_space_name_without_rewriting_owner_markdown(
    tmp_path: Path,
) -> None:
    root = tmp_path / "brain"
    tasks = open_local_engine(compile_single_user_local(root))
    space = tasks.inbox.create_space("Studio", delivery_id="reconcile.space")
    capture = tasks.capture.accept(
        TextPayload("Original canonical body\n"),
        delivery_id="reconcile.capture",
        action=CaptureAction.CANONICAL_NOTE,
        space_id=space.space_id,
    )
    page = next((root / "content" / "spaces").rglob("page_*.md"))
    original_page = page.read_bytes()
    parsed_page = parse_markdown(original_page)
    page.write_bytes(
        render_markdown(
            fields={
                **parsed_page.fields,
                "modified_at": "2026-09-01T12:30:00Z",
                "title": "Edited title",
            },
            body="Edited owner Markdown body\n",
        ).encode("utf-8")
    )
    space_file = next((root / "content" / "spaces").rglob("_space.md"))
    original_space = space_file.read_bytes()
    parsed_space = parse_markdown(original_space)
    space_file.write_bytes(
        render_markdown(fields={**parsed_space.fields, "name": "Renamed Studio"}, body="").encode(
            "utf-8"
        )
    )
    expected_page = page.read_bytes()
    expected_space = space_file.read_bytes()
    profile = open_existing_single_user_local(root)

    with acquire_daemon_authority(profile) as authority:
        authoritative = open_authoritative_local_engine(profile, authority)
        receipt = authoritative.reconciliation.reconcile()

    refreshed = tasks.retrieval.search("Edited owner Markdown")[0]
    renamed = tasks.inbox.spaces()[0]

    assert receipt.status == "reconciled"
    assert receipt.page_updates == 1
    assert receipt.space_updates == 1
    assert refreshed.result_id != capture.capture_id
    assert refreshed.title == "Edited title"
    assert renamed.space_id == space.space_id
    assert renamed.slug == space.slug
    assert renamed.name == "Renamed Studio"
    assert page.read_bytes() == expected_page
    assert space_file.read_bytes() == expected_space
