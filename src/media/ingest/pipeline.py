"""Ingestion pipeline orchestration."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.ids import new_id
from src.db.models import ArtifactRow, SourceRow
from src.domain.models import SourceType
from src.media.ffmpeg.probe import probe
from src.media.ffmpeg.transcode import extract_audio, generate_proxy
from src.media.ingest.downloader import download_youtube_video
from src.media.ingest.uploader import copy_uploaded_file
from src.storage.base import ArtifactStore
from src.telemetry.logging import get_logger

logger = get_logger(__name__)


def compute_sha256(path: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            sha256.update(block)
    return sha256.hexdigest()


async def run_ingest(
    source_id: str,
    uri: str,
    source_type: SourceType,
    store: ArtifactStore,
    db: AsyncSession,
) -> list[ArtifactRow]:
    """
    Orchestrate the ingestion of a media source.
    Downloads/copies, computes checksum, probes, extracts audio, generates proxy.
    Stores artifacts and updates the Source record in the DB.
    """
    logger.info("ingest_pipeline_started", source_id=source_id, uri=uri)
    
    with tempfile.TemporaryDirectory(prefix="clipper_ingest_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        
        # 1. Acquire source file
        if source_type == SourceType.YOUTUBE:
            local_source_path = download_youtube_video(uri, temp_dir)
        elif source_type == SourceType.UPLOAD:
            local_source_path = copy_uploaded_file(uri, temp_dir)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
            
        # 2. Compute checksum
        checksum = compute_sha256(local_source_path)
        
        # 3. Probe metadata
        probe_result = probe(local_source_path)
        
        # 4. Generate audio and proxy
        audio_path = temp_dir / f"{source_id}_audio.wav"
        extract_audio(local_source_path, audio_path)
        
        proxy_path = temp_dir / f"{source_id}_proxy.mp4"
        generate_proxy(local_source_path, proxy_path)
        
        # 5. Store artifacts
        stage = "ingest"
        version = "v1"
        cache_key_base = f"{stage}/{source_id}/{version}/{checksum}"
        
        artifacts = []
        
        # Define artifacts to store
        files_to_store = {
            "source.mp4": local_source_path,
            "audio.wav": audio_path,
            "proxy.mp4": proxy_path,
        }
        
        # Also store probe info as JSON
        probe_json_path = temp_dir / "probe.json"
        probe_json_path.write_text(json.dumps(probe_result.raw))
        files_to_store["probe.json"] = probe_json_path

        for filename, path in files_to_store.items():
            key = f"{cache_key_base}/{filename}"
            # Check idempotency
            if not await store.exists(key):
                uri_store = await store.put(key, path.read_bytes())
            else:
                uri_store = await store.get_uri(key)
                
            # Create DB record if not exists
            result = await db.execute(
                select(ArtifactRow).where(
                    ArtifactRow.source_id == source_id,
                    ArtifactRow.stage == stage,
                    ArtifactRow.version == version,
                    ArtifactRow.storage_uri == uri_store
                )
            )
            art_row = result.scalar_one_or_none()
            if not art_row:
                art_row = ArtifactRow(
                    id=new_id(),
                    source_id=source_id,
                    stage=stage,
                    version=version,
                    content_hash=checksum,
                    storage_uri=uri_store,
                    extra_metadata={"filename": filename}
                )
                db.add(art_row)
            artifacts.append(art_row)
            
        # 6. Update source record
        result = await db.execute(select(SourceRow).where(SourceRow.id == source_id))
        source_row = result.scalar_one_or_none()
        if source_row:
            source_row.checksum = checksum
            source_row.duration_seconds = probe_result.duration_seconds
            source_row.width = probe_result.width
            source_row.height = probe_result.height
            source_row.fps = probe_result.fps
            
        await db.commit()
        
    logger.info("ingest_pipeline_completed", source_id=source_id, checksum=checksum)
    return artifacts
