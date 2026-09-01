from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from open_brain.engine import (
    DaemonAuthorityError,
    DaemonAuthorityRootMismatchError,
    DaemonAuthorityStaleError,
    LocalEngineContext,
    TextPayload,
    acquire_daemon_authority,
)
from open_brain.engine.authority import DaemonAuthorityCapability
from open_brain.profile import compile_single_user_local, open_existing_single_user_local
from open_brain.services.appliance_application import ApplianceApplication
from open_brain.storage.locks import LockBusyError


def _existing_profile(root: Path) -> LocalEngineContext:
    compile_single_user_local(root)
    return open_existing_single_user_local(root)


def test_daemon_authority_capability_is_issuer_created() -> None:
    with pytest.raises(TypeError, match="issuer-created"):
        DaemonAuthorityCapability()


def test_appliance_application_constructor_cannot_accept_mutating_tasks() -> None:
    assert "mutations" not in inspect.signature(ApplianceApplication).parameters


def test_appliance_mutating_composition_rejects_missing_stale_and_wrong_root_authority(
    tmp_path: Path,
) -> None:
    root = tmp_path / "brain"
    other_root = tmp_path / "other-brain"
    profile = _existing_profile(root)
    _existing_profile(other_root)

    with pytest.raises(DaemonAuthorityError, match="missing"):
        ApplianceApplication.open_mutating(root)

    with acquire_daemon_authority(profile) as authority, pytest.raises(
        DaemonAuthorityRootMismatchError,
        match="root mismatch",
    ):
        ApplianceApplication.open_mutating(other_root, authority=authority)

    with pytest.raises(DaemonAuthorityStaleError, match="stale"):
        ApplianceApplication.open_mutating(root, authority=authority)


def test_daemon_authority_is_process_exclusive_and_enables_shared_writer_mutations(
    tmp_path: Path,
) -> None:
    root = tmp_path / "brain"
    profile = _existing_profile(root)

    with acquire_daemon_authority(profile) as authority:
        with pytest.raises(
            LockBusyError,
            match="lease already held by this process",
        ), acquire_daemon_authority(profile):
            pass

        application = ApplianceApplication.open_mutating(root, authority=authority)
        assert application.mutations is not None

        receipt = application.mutations.capture.accept(
            TextPayload("Synthetic daemon-authorized capture"),
            delivery_id="delivery.appliance.daemon-authority",
        )

        assert receipt.state == "inbox"
        result = application.retrieval.search("daemon-authorized capture")[0]
        assert result.capture_id == receipt.capture_id

    with pytest.raises(DaemonAuthorityStaleError, match="stale"):
        assert application.mutations is not None
        application.mutations.capture.accept(
            TextPayload("Synthetic stale authority capture"),
            delivery_id="delivery.appliance.daemon-authority.stale",
        )
