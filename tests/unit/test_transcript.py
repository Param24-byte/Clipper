"""Unit tests for the transcription pipeline."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.ids import new_id
from src.db.models import ArtifactRow
from src.intelligence.transcript.pipeline import run_transcription


@pytest.fixture
def mock_transcribe_audio():
    with patch("src.intelligence.transcript.pipeline.transcribe_audio") as mock:
        yield mock


@pytest.mark.asyncio
async def test_run_transcription(db: AsyncSession, mock_transcribe_audio):
    source_id = new_id()
    
    # 1. Setup ingest audio artifact
    audio_art = ArtifactRow(
        id=new_id(),
        source_id=source_id,
        stage="ingest",
        version="v1",
        content_hash="hash123",
        storage_uri="local://ingest/01HYBXXXXX/v1/hash123/audio.wav",
        extra_metadata={"filename": "audio.wav"}
    )
    db.add(audio_art)
    await db.commit()
    
    # 2. Mock store
    class MockStore:
        async def get(self, key): return b"fake audio data"
        async def put(self, key, data, content_type=None): return f"local://{key}"
        
    store = MockStore()
    
    # 3. Mock Whisper
    mock_transcribe_audio.return_value = {
        "duration": 10.0,
        "language": "en",
        "segments": [{"start": 0.0, "end": 2.0, "text": "Hello"}],
        "words": [{"start": 0.0, "end": 1.0, "word": "Hello", "probability": 0.9}]
    }
    
    # 4. Run
    transcript_art = await run_transcription(source_id, store, db)
    
    assert transcript_art.stage == "transcribe"
    assert transcript_art.content_hash == "hash123"
    assert transcript_art.extra_metadata["filename"] == "transcript.json"
