"""Canonical lock vocabulary shared across engine implementations."""

from enum import StrEnum


class LockScope(StrEnum):
    NONE = "none"
    SHARED_WRITER = "shared-writer"
    INDEX = "index"
    BACKUP_PROFILE = "backup-profile"
    INGRESS = "ingress"
    PORTABILITY_PROMOTION = "portability-promotion"
