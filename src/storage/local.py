"""Local filesystem artifact store — development implementation."""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.storage.base import ArtifactStore
from src.telemetry.logging import get_logger

logger = get_logger(__name__)


class LocalArtifactStore(ArtifactStore):
    """
    Stores artifacts on the local filesystem under `root_dir`.

    Key format: `<stage>/<source_id>/<filename>`
    URI format:  `local://<absolute_path>`
    """

    def __init__(self, root_dir: str | Path) -> None:
        self._root = Path(root_dir).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        logger.info("local_artifact_store_ready", root=str(self._root))

    def _path_for(self, key: str) -> Path:
        # Prevent path traversal — strip leading slashes and dots
        safe_key = key.lstrip("/").replace("..", "__")
        return self._root / safe_key

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, path.write_bytes, data)
        uri = f"local://{path}"
        logger.debug("artifact_stored", key=key, uri=uri, size=len(data))
        return uri

    async def get(self, key: str) -> bytes:
        path = self._path_for(key)
        if not path.exists():
            raise KeyError(f"Artifact not found: {key}")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, path.read_bytes)

    async def exists(self, key: str) -> bool:
        return self._path_for(key).exists()

    async def delete(self, key: str) -> None:
        path = self._path_for(key)
        if path.exists():
            path.unlink()
            logger.debug("artifact_deleted", key=key)

    async def get_uri(self, key: str) -> str:
        return f"local://{self._path_for(key)}"
