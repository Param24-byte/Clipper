"""Unit tests for EDL generator."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.ids import new_id
from src.db.models import ClipRow, ArtifactRow
from src.export.edl_generator import generate_edl


@pytest.mark.asyncio
async def test_generate_edl(db: AsyncSession):
    source_id = new_id()
    project_id = new_id()
    
    # 1. Setup clips
    c1 = ClipRow(id=new_id(), source_id=source_id, project_id=project_id, start_time=10.0, end_time=15.0, score=10.0, status="selected")
    c2 = ClipRow(id=new_id(), source_id=source_id, project_id=project_id, start_time=20.0, end_time=22.0, score=30.0, status="selected")
    c3 = ClipRow(id=new_id(), source_id=source_id, project_id=project_id, start_time=4.0, end_time=5.0, score=20.0, status="rejected")
    
    db.add_all([c1, c2, c3])
    await db.commit()
    
    # Mock store
    class MockStore:
        async def put(self, key, data, content_type=None):
            self.data = data
            return f"local://{key}"
    store = MockStore()
    
    # 2. Generate EDL
    artifact = await generate_edl(source_id, store, db)
    
    # 3. Verify
    assert artifact.stage == "generate_edl"
    assert artifact.extra_metadata["filename"] == "export.edl"
    
    # Check EDL content
    edl_text = store.data.decode("utf-8")
    assert "TITLE: CLIPPER EXPORT" in edl_text
    # Should only contain 2 events for c1 and c2
    assert "001  AX       V     C" in edl_text
    assert "002  AX       V     C" in edl_text
    assert "003  AX       V     C" not in edl_text
