"""Pure capture extraction contracts and implementations."""

from __future__ import annotations

from dataclasses import dataclass

from open_brain.engine import RawAssetRef


@dataclass(frozen=True, slots=True)
class ExtractionRequest:
    """Bounded, already-canonical input supplied to an extractor."""

    capture_id: str = ""
    url: str = ""
    text: str = ""
    assets: tuple[RawAssetRef, ...] = ()
    timeout_seconds: float = 10.0
    max_bytes: int = 2 * 1024 * 1024
    max_redirects: int = 3


__all__ = ["ExtractionRequest"]
