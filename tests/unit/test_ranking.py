"""Unit tests for clip ranking."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.ids import new_id
from src.db.models import ClipRow
from src.intelligence.ranking.ranker import rank_clips


@pytest.mark.asyncio
async def test_rank_clips(db: AsyncSession):
    source_id = new_id()
    project_id = new_id()
    
    # 1. Setup clips
    c1 = ClipRow(id=new_id(), source_id=source_id, project_id=project_id, start_time=0.0, end_time=1.0, score=10.0, status="draft")
    c2 = ClipRow(id=new_id(), source_id=source_id, project_id=project_id, start_time=2.0, end_time=3.0, score=30.0, status="draft")
    c3 = ClipRow(id=new_id(), source_id=source_id, project_id=project_id, start_time=4.0, end_time=5.0, score=20.0, status="draft")
    
    db.add_all([c1, c2, c3])
    await db.commit()
    
    # 2. Rank top 2
    selected_ids = await rank_clips(source_id, db, top_n=2)
    
    # 3. Assertions
    assert len(selected_ids) == 2
    # Should select c2 (score 30) and c3 (score 20)
    assert set(selected_ids) == {c2.id, c3.id}
    
    # Verify DB state
    res = await db.execute(select(ClipRow).where(ClipRow.source_id == source_id))
    clips = res.scalars().all()
    
    for c in clips:
        if c.id in selected_ids:
            assert c.status == "selected"
        else:
            assert c.status == "rejected"
