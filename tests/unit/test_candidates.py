"""Unit tests for candidate discovery."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.ids import new_id
from src.db.models import ArtifactRow, CandidateRow
from src.intelligence.candidates.pipeline import discover_candidates
from src.domain.models import Candidate


@pytest.fixture
def mock_llm_adapter():
    with patch("src.intelligence.candidates.semantic.get_llm_adapter") as mock_get:
        mock_adapter = MagicMock()
        mock_get.return_value = mock_adapter
        yield mock_adapter


@pytest.mark.asyncio
async def test_discover_candidates(db: AsyncSession, mock_llm_adapter):
    source_id = new_id()
    
    # 1. Setup index artifact
    index_art = ArtifactRow(
        id=new_id(),
        source_id=source_id,
        stage="index",
        version="v1",
        content_hash="hash123",
        storage_uri=f"local://index/{source_id}/v1/hash123/media_index.json",
        extra_metadata={"filename": "media_index.json"}
    )
    db.add(index_art)
    await db.commit()
    
    # 2. Mock store
    fake_index = {
        "sentences": [
            {"start": 0.0, "end": 1.5, "text": "Wow."}, # Audio candidate (< 2s)
            {"start": 2.0, "end": 6.0, "text": "This is a really strong and controversial statement that will get clicks."},
        ]
    }
    class MockStore:
        async def get(self, key): return json.dumps(fake_index).encode("utf-8")
    store = MockStore()
    
    # 3. Mock LLM
    async def mock_generate_json(prompt, *args, **kwargs):
        return {
            "moments": [
                {
                    "start": 2.0,
                    "end": 6.0,
                    "reason": "Very controversial",
                    "quote": "This is a really strong and controversial statement that will get clicks."
                }
            ]
        }
    mock_llm_adapter.generate_json.side_effect = mock_generate_json
    
    # 4. Run
    candidate_ids = await discover_candidates(source_id, store, db)
    
    # 5. Verify
    assert len(candidate_ids) == 2
    
    result = await db.execute(select(CandidateRow).where(CandidateRow.source_id == source_id))
    rows = result.scalars().all()
    
    assert len(rows) == 2
    
    audio_cand = next(r for r in rows if "HighEnergySpike" in r.generators)
    assert audio_cand.event_start == 0.0
    assert audio_cand.event_end == 1.5
    
    semantic_cand = next(r for r in rows if "SemanticStrongStatement" in r.generators)
    assert semantic_cand.event_start == 2.0
    assert semantic_cand.event_end == 6.0
    assert semantic_cand.evidence["quote"] == "This is a really strong and controversial statement that will get clicks."
