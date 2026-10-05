"""Storage package — exposes ArtifactStore interface and factory."""

from __future__ import annotations

from src.storage.base import ArtifactStore
from src.storage.local import LocalArtifactStore


def get_artifact_store() -> ArtifactStore:
    """Factory — returns the correct backend based on settings."""
    from src.config import get_settings
    settings = get_settings()
    if settings.artifact_storage_backend == "local":
        return LocalArtifactStore(settings.artifact_local_root)
    raise NotImplementedError(f"Storage backend not implemented: {settings.artifact_storage_backend}")


__all__ = ["ArtifactStore", "LocalArtifactStore", "get_artifact_store"]
