"""Media Index Builder."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.ids import new_id
from src.db.models import ArtifactRow
from src.intelligence.index.signals import detect_silence
from src.storage.base import ArtifactStore
from src.telemetry.logging import get_logger

logger = get_logger(__name__)


async def build_media_index(
    source_id: str,
    store: ArtifactStore,
    db: AsyncSession,
) -> ArtifactRow:
    """
    Orchestrate building the media index.
    Needs transcript and audio artifacts.
    """
    logger.info("media_index_pipeline_started", source_id=source_id)

    # 1. Find transcript and audio artifacts
    result = await db.execute(
        select(ArtifactRow).where(
            ArtifactRow.source_id == source_id,
            ArtifactRow.stage == "transcribe",
        )
    )
    transcript_art = result.scalar_one_or_none()
    if not transcript_art:
        raise ValueError(f"No transcript artifact found for source {source_id}")
        
    result = await db.execute(
        select(ArtifactRow).where(
            ArtifactRow.source_id == source_id,
            ArtifactRow.stage == "ingest",
        )
    )
    audio_art = next((a for a in result.scalars() if a.extra_metadata.get("filename") == "audio.wav"), None)
    if not audio_art:
        raise ValueError(f"No audio.wav artifact found for source {source_id}")

    # 2. Check idempotency
    stage = "index"
    version = "v1"
    # Tied to transcript hash so if transcript changes, index is rebuilt
    cache_key = f"{stage}/{source_id}/{version}/{transcript_art.content_hash}/media_index.json"

    result = await db.execute(
        select(ArtifactRow).where(
            ArtifactRow.source_id == source_id,
            ArtifactRow.stage == stage,
            ArtifactRow.version == version,
            ArtifactRow.content_hash == transcript_art.content_hash
        )
    )
    existing_art = result.scalar_one_or_none()
    if existing_art:
        logger.info("media_index_pipeline_cached", source_id=source_id)
        return existing_art

    with tempfile.TemporaryDirectory(prefix="clipper_index_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        audio_path = temp_dir / "audio.wav"

        # 3. Download audio
        audio_data = await store.get(audio_art.storage_uri.replace("local://", ""))
        audio_path.write_bytes(audio_data)
        
        # Download transcript
        transcript_data = await store.get(transcript_art.storage_uri.replace("local://", ""))
        transcript = json.loads(transcript_data)

        # 4. Compute signals
        silence_regions = detect_silence(audio_path)
        
        # Build sentences from transcript segments
        sentences = []
        for seg in transcript.get("segments", []):
            sentences.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"]
            })

        # Assemble index
        index_data = {
            "schema_version": "1",
            "source_id": source_id,
            "duration": transcript.get("duration", 0.0),
            "words": transcript.get("words", []),
            "sentences": sentences,
            "intervals": [], # Stub for V0.2, will be expanded later
            "silence_regions": silence_regions,
            "scene_boundaries": [], # Stub, opencv needed
        }

        # 5. Store result
        index_json = json.dumps(index_data)
        uri_store = await store.put(cache_key, index_json.encode("utf-8"), content_type="application/json")

        art_row = ArtifactRow(
            id=new_id(),
            source_id=source_id,
            stage=stage,
            version=version,
            content_hash=transcript_art.content_hash,
            storage_uri=uri_store,
            extra_metadata={"filename": "media_index.json"}
        )
        db.add(art_row)
        await db.commit()

    logger.info("media_index_pipeline_completed", source_id=source_id)
    return art_row
