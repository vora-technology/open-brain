from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from open_brain.capture.models import CaptureWorkItem
from open_brain.capture.queue import FilesystemCaptureQueue
from open_brain.core.ids import canonical_json_bytes
from open_brain.core.models import CaptureSource, PrivacyTier
from open_brain.core.ports import PutResult
from open_brain.production.imessage import (
    ImessageConfigError,
    ProductionImessageIngress,
    compose_production_imessage_ingress,
    load_private_imessage_config,
)

FIXED_TIME = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


@dataclass
class _History:
    payload: bytes
    cursors: list[int]

    def history(self, *, chat_id: str, after_rowid: int) -> bytes:
        assert chat_id == "synthetic-chat"
        self.cursors.append(after_rowid)
        return self.payload


def _config(path: Path) -> Path:
    path.write_bytes(
        canonical_json_bytes(
            {
                "schema_version": 1,
                "chat_id": "synthetic-chat",
                "allowed_senders": ["owner@example.test"],
            }
        )
    )
    path.chmod(0o600)
    return path


def _history_payload() -> bytes:
    messages = (
        {
            "rowid": 1,
            "chat_id": "other-chat",
            "sender": "owner@example.test",
            "text": "Synthetic wrong chat",
            "timestamp": "2026-08-25T11:55:00Z",
        },
        {
            "rowid": 2,
            "chat_id": "synthetic-chat",
            "sender": "other@example.test",
            "text": "Synthetic wrong sender",
            "timestamp": "2026-08-25T11:56:00Z",
        },
        {
            "rowid": 3,
            "chat_id": "synthetic-chat",
            "sender": "owner@example.test",
            "text": "Synthetic self message",
            "timestamp": "2026-08-25T11:57:00Z",
            "is_from_me": True,
        },
        {
            "rowid": 4,
            "chat_id": "synthetic-chat",
            "sender": "owner@example.test",
            "text": "Synthetic retained message",
            "timestamp": "2026-08-25T11:58:00Z",
        },
        {
            "rowid": 5,
            "chat_id": "synthetic-chat",
            "sender": "owner@example.test",
            "text": "Synthetic retained message",
            "timestamp": "2026-08-25T11:59:00Z",
        },
    )
    return b"\n".join(canonical_json_bytes(message) for message in messages)


def test_imessage_ingress_filters_appends_then_advances_cursor_and_replays(
    tmp_path: Path,
) -> None:
    queue = FilesystemCaptureQueue(tmp_path / "queue")
    history = _History(_history_payload(), [])
    runtime = compose_production_imessage_ingress(
        config_path=_config(tmp_path / "imessage.json"),
        state_root=tmp_path / "state",
        queue=queue,
        history_client=history,
    )

    first = runtime.run_once()
    replay = runtime.run_once()

    assert first.scanned_count == 5
    assert first.created_count == 2
    assert first.duplicate_count == 0
    assert first.cursor_rowid == 5
    assert replay.scanned_count == 0
    assert replay.created_count == 0
    assert history.cursors == [0, 5]
    assert "Synthetic retained message" not in repr(first)
    assert "owner@example.test" not in repr(first)
    assert queue.pending_snapshot().pending_count == 2
    lease = queue.claim(worker_id="synthetic", now=FIXED_TIME)
    assert lease is not None
    assert lease.item.envelope.capture_source is CaptureSource.INTEGRATION
    assert lease.item.envelope.privacy_decision.tier is PrivacyTier.PERSONAL
    assert lease.item.envelope.shared_text == "Synthetic retained message"


class _FailingQueue:
    def enqueue(
        self,
        item: CaptureWorkItem,
        *,
        item_id: str,
        payload_digest: str,
    ) -> PutResult:
        del item, item_id, payload_digest
        raise RuntimeError("synthetic queue failure")


def test_imessage_cursor_does_not_advance_when_queue_append_fails(tmp_path: Path) -> None:
    history = _History(_history_payload(), [])
    runtime = ProductionImessageIngress(
        config=load_private_imessage_config(_config(tmp_path / "imessage.json")),
        state_root=tmp_path / "state",
        queue=_FailingQueue(),
        history_client=history,
    )

    with pytest.raises(RuntimeError, match="synthetic queue failure"):
        runtime.run_once()

    retry_queue = FilesystemCaptureQueue(tmp_path / "queue")
    retry = ProductionImessageIngress(
        config=load_private_imessage_config(tmp_path / "imessage.json"),
        state_root=tmp_path / "state",
        queue=retry_queue,
        history_client=history,
    ).run_once()
    assert retry.created_count == 2
    assert history.cursors == [0, 0]


@dataclass
class _TransientHistory:
    payload: bytes
    calls: int = 0

    def history(self, *, chat_id: str, after_rowid: int) -> bytes:
        assert chat_id == "synthetic-chat"
        assert after_rowid == 0
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("synthetic transient history failure")
        return self.payload


def test_imessage_keepalive_retries_transient_failure_then_uses_idle_interval(
    tmp_path: Path,
) -> None:
    history = _TransientHistory(_history_payload())
    sleeps: list[float] = []
    runtime = ProductionImessageIngress(
        config=load_private_imessage_config(_config(tmp_path / "imessage.json")),
        state_root=tmp_path / "state",
        queue=FilesystemCaptureQueue(tmp_path / "queue"),
        history_client=history,
    )

    runtime.run_forever(
        should_stop=lambda: len(sleeps) == 2,
        sleep=sleeps.append,
        idle_seconds=7.0,
        failure_seconds=11.0,
    )

    assert history.calls == 2
    assert sleeps == [11.0, 7.0]
    assert FilesystemCaptureQueue(tmp_path / "queue").pending_snapshot().pending_count == 2


def test_imessage_config_requires_owner_only_regular_canonical_file(tmp_path: Path) -> None:
    config = _config(tmp_path / "imessage.json")
    config.chmod(0o644)

    with pytest.raises(ImessageConfigError, match="private iMessage config"):
        load_private_imessage_config(config)

    config.chmod(0o600)
    linked = tmp_path / "linked.json"
    linked.symlink_to(config)
    with pytest.raises(ImessageConfigError, match="private iMessage config"):
        load_private_imessage_config(linked)
