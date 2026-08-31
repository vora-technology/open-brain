"""Closed, local-first text-model providers."""

from .base import ProviderFailure, ProviderService, lazy_cloud_factory
from .deterministic import DeterministicDistillationProvider
from .local import LocalProvider, LocalTransport
from .transcription import (
    TranscriptionProvider,
    TranscriptionRequest,
    TranscriptionResult,
    TranscriptionService,
)

__all__ = [
    "LocalProvider",
    "LocalTransport",
    "ProviderFailure",
    "ProviderService",
    "DeterministicDistillationProvider",
    "TranscriptionProvider",
    "TranscriptionRequest",
    "TranscriptionResult",
    "TranscriptionService",
    "lazy_cloud_factory",
]
