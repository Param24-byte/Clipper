"""Unit tests for the media index builder."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.ids import new_id
from src.db.models import ArtifactRow
from src.intelligence.index.builder import build_media_index
from src.intelligence.index.query import MediaIndexQuery


@pytest.fixture
def mock_detect_silence():
    with patch("src.intelligence.index.builder.detect_silence") as mock:
        yield mock


@pytest.mark.asyncio
async def test_build_media_index(db: AsyncSession, mock_detect_silence):
    source_id = new_id()
    
    # 1. Setup transcript & audio artifacts
    audio_art = ArtifactRow(
        id=new_id(),
        source_id=source_id,
        stage="ingest",
        version="v1",
        content_hash="hash123",
        storage_uri=f"local://ingest/{source_id}/v1/hash123/audio.wav",
        extra_metadata={"filename": "audio.wav"}
    )
    transcript_art = ArtifactRow(
        id=new_id(),
        source_id=source_id,
        stage="transcribe",
        version="v1",
        content_hash="hash123",
        storage_uri=f"local://transcribe/{source_id}/v1/hash123/transcript.json",
        extra_metadata={"filename": "transcript.json"}
    )
    db.add_all([audio_art, transcript_art])
    await db.commit()
    
    # 2. Mock store
    fake_transcript = {
        "duration": 10.0,
        "segments": [{"start": 0.0, "end": 2.0, "text": "Hello world"}],
        "words": [{"start": 0.0, "end": 1.0, "word": "Hello"}]
    }
    class MockStore:
        async def get(self, key):
            if "audio.wav" in key:
                return b"fake audio data"
            return json.dumps(fake_transcript).encode("utf-8")
            
        async def put(self, key, data, content_type=None): return f"local://{key}"
        
    store = MockStore()
    
    # 3. Mock silence
    mock_detect_silence.return_value = [{"start": 5.0, "end": 8.0}]
    
    # 4. Run
    index_art = await build_media_index(source_id, store, db)
    
    assert index_art.stage == "index"
    assert index_art.content_hash == "hash123"
    assert index_art.extra_metadata["filename"] == "media_index.json"
    
    
def test_media_index_query():
    data = {
        "sentences": [
            {"start": 1.0, "end": 2.0, "text": "One."},
            {"start": 2.5, "end": 4.0, "text": "Two."},
        ],
        "words": [
            {"start": 1.0, "end": 1.5, "word": "One"},
            {"start": 2.5, "end": 3.0, "word": "Two"}
        ]
    }
    
    query = MediaIndexQuery(data)
    
    sents = query.get_sentences_in_range(0.0, 3.0)
    assert len(sents) == 1
    assert sents[0]["text"] == "One."
    
    words = query.get_words_in_range(2.0, 5.0)
    assert len(words) == 1
    assert words[0]["word"] == "Two"
