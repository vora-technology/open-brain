"""Generate an ephemeral artifact-only P4-W6 clean-host fixture."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import tempfile
import uuid
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from typing import Final

from open_brain_engine.engine import ProposalDraft, TextPayload, open_local_engine

from open_brain.profile import open_existing_single_user_local
from open_brain.services.appliance_auth import derive_appliance_credential
from open_brain.services.appliance_init import initialize_appliance

_FAILURE: Final = "clean-host fixture operation failed"
_MAXIMUM_CONTROL_BYTES: Final = 64 * 1024


class CleanHostFixtureError(RuntimeError):
    """Fixture generation failed without exposing ephemeral controller data."""


def create_clean_host_fixture(destination: Path) -> dict[str, object]:
    """Create six pending sibling proposals plus private ephemeral controller data."""
    created = False
    try:
        output = destination.resolve()
        if destination.exists() or destination.is_symlink():
            raise CleanHostFixtureError(_FAILURE)
        output.mkdir(parents=True, mode=0o700)
        created = True
        with tempfile.TemporaryDirectory(prefix="ob-p4w6-fixture-", dir="/tmp") as raw:
            live = Path(raw).resolve() / "live"
            initialize_appliance(live, starter_spaces=("P4W6 Reviews",))
            tasks = open_local_engine(open_existing_single_user_local(live))
            space = tasks.inbox.spaces()[0]
            capture = tasks.capture.accept(
                TextPayload("P4W6 clean-host sibling source"),
                delivery_id="p4w6.fixture.capture",
                space_id=space.space_id,
            )
            proposals = tasks.review.propose(
                capture.capture_id,
                tuple(
                    ProposalDraft(
                        f"P4W6 sibling {index}",
                        f"# Original P4W6 sibling meaning {index}\n",
                    )
                    for index in range(6)
                ),
                delivery_id="p4w6.fixture.proposals",
            )
            receipt = tasks.portability.export(
                output / "portable-root",
                export_id=f"export_{uuid.uuid4()}",
            )
            if receipt.status != "exported":
                raise CleanHostFixtureError(_FAILURE)
            backup = Path(raw).resolve() / "backup"
            backup_receipt = tasks.backup.create(
                backup,
                backup_id=f"backup_{uuid.uuid4()}",
            )
            runtime_root = output / "runtime-root"
            runtime_root.mkdir(mode=0o700)
            restore_receipt = tasks.backup.restore(backup, runtime_root)
            if backup_receipt.status != "created" or restore_receipt.status != "restored":
                raise CleanHostFixtureError(_FAILURE)
        seed = "p4w6-fixture-" + secrets.token_urlsafe(32)
        controller = {
            "browser_bootstrap": derive_appliance_credential(
                seed,
                purpose="browser-bootstrap",
            ),
            "capture_id": capture.capture_id,
            "fixture_seed": seed,
            "proposal_ids": [proposal.proposal_id for proposal in proposals],
            "schema_version": 1,
        }
        _write_private_json(output / "controller.json", controller)
        return {
            "capture_count": 1,
            "proposal_count": len(proposals),
            "schema_version": 1,
            "status": "created",
        }
    except CleanHostFixtureError:
        if created:
            _remove_created_tree(destination)
        raise
    except Exception as error:
        if created:
            _remove_created_tree(destination)
        raise CleanHostFixtureError(_FAILURE) from error


def _write_private_json(path: Path, value: dict[str, object]) -> None:
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    if len(payload) > _MAXIMUM_CONTROL_BYTES:
        raise CleanHostFixtureError(_FAILURE)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        with suppress(OSError):
            os.close(descriptor)
        raise


def _remove_created_tree(path: Path) -> None:
    with suppress(OSError):
        if path.exists() and not path.is_symlink():
            shutil.rmtree(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.phase4.clean_host_fixture")
    parser.add_argument("--output", type=Path, required=True)
    namespace = parser.parse_args(argv)
    try:
        result = create_clean_host_fixture(namespace.output)
        exit_code = 0
    except CleanHostFixtureError:
        result = {"status": "failed"}
        exit_code = 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
