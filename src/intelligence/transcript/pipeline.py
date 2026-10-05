"""Transcript pipeline orchestration."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.ids import new_id
from src.db.models import ArtifactRow
from src.intelligence.transcript.whisper_adapter import transcribe_audio
from src.storage.base import ArtifactStore
from src.telemetry.logging import get_logger

logger = get_logger(__name__)


async def run_transcription(
    source_id: str,
    store: ArtifactStore,
    db: AsyncSession,
) -> ArtifactRow:
    """
    Orchestrate transcription of an audio artifact.
    Finds the audio.wav artifact from the ingest stage, runs Whisper,
    and stores transcript.json.
    """
    logger.info("transcription_pipeline_started", source_id=source_id)

    # 1. Find audio artifact
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
    stage = "transcribe"
    version = "v1"
    cache_key = f"{stage}/{source_id}/{version}/{audio_art.content_hash}/transcript.json"

    # We do a DB lookup to see if we already have the transcript artifact
    result = await db.execute(
        select(ArtifactRow).where(
            ArtifactRow.source_id == source_id,
            ArtifactRow.stage == stage,
            ArtifactRow.version == version,
            ArtifactRow.content_hash == audio_art.content_hash
        )
    )
    existing_art = result.scalar_one_or_none()
    if existing_art:
        logger.info("transcription_pipeline_cached", source_id=source_id)
        return existing_art

    with tempfile.TemporaryDirectory(prefix="clipper_transcribe_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        audio_path = temp_dir / "audio.wav"

        # 3. Download audio artifact from store
        audio_data = await store.get(audio_art.storage_uri.replace("local://", ""))
        audio_path.write_bytes(audio_data)

        # 4. Run Whisper
        transcript_data = transcribe_audio(audio_path, model_size="tiny") # use tiny for speed in dev

        # 5. Store result
        transcript_json = json.dumps(transcript_data)
        uri_store = await store.put(cache_key, transcript_json.encode("utf-8"), content_type="application/json")

        art_row = ArtifactRow(
            id=new_id(),
            source_id=source_id,
            stage=stage,
            version=version,
            content_hash=audio_art.content_hash, # tied to audio hash
            storage_uri=uri_store,
            extra_metadata={"filename": "transcript.json"}
        )
        db.add(art_row)
        await db.commit()

    logger.info("transcription_pipeline_completed", source_id=source_id)
    return art_row
