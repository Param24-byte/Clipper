"""
ArtifactStore ABC.

All implementations must satisfy this interface.
The local filesystem implementation is the default for development.
An S3 adapter can be swapped in without touching the pipeline.
"""

from __future__ import annotations

import abc
from pathlib import Path


class ArtifactStore(abc.ABC):
    """Abstract artifact storage backend."""

    @abc.abstractmethod
    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """
        Store `data` under `key`.
        Returns the storage URI (e.g., `local://artifacts/...` or `s3://bucket/...`).
        """

    @abc.abstractmethod
    async def get(self, key: str) -> bytes:
        """Retrieve artifact by key. Raises KeyError if not found."""

    @abc.abstractmethod
    async def exists(self, key: str) -> bool:
        """Return True if the artifact exists."""

    @abc.abstractmethod
    async def delete(self, key: str) -> None:
        """Delete artifact. No-op if not found."""

    @abc.abstractmethod
    async def get_uri(self, key: str) -> str:
        """Return the canonical storage URI for a key without fetching data."""
