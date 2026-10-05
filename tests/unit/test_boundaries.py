"""Unit tests for boundary resolver."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.ids import new_id
from src.db.models import SourceRow, CandidateRow, ClipRow, ProjectRow
from src.intelligence.boundaries.resolver import resolve_boundaries


@pytest.mark.asyncio
async def test_resolve_boundaries(db: AsyncSession):
    project_id = new_id()
    source_id = new_id()
    
    # Setup project and source
    project = ProjectRow(id=project_id, owner_id="user1", name="Test")
    source = SourceRow(id=source_id, project_id=project_id, type="youtube", uri="http://test")
    db.add(project)
    db.add(source)
    await db.commit()
    
    # Add some overlapping candidates
    c1 = CandidateRow(
        id=new_id(), source_id=source_id, event_start=10.0, event_end=15.0,
        generators=["g1"], reason_codes=["r1"]
    )
    c2 = CandidateRow(
        id=new_id(), source_id=source_id, event_start=14.0, event_end=20.0,
        generators=["g2"], reason_codes=["r2"]
    )
    c3 = CandidateRow(
        id=new_id(), source_id=source_id, event_start=30.0, event_end=35.0,
        generators=["g3"], reason_codes=["r3"]
    )
    db.add_all([c1, c2, c3])
    await db.commit()
    
    # Run
    clip_ids = await resolve_boundaries(source_id, db)
    
    assert len(clip_ids) == 2
    
    # Validate in db
    res = await db.execute(select(ClipRow).where(ClipRow.source_id == source_id).order_by(ClipRow.start_time))
    clips = res.scalars().all()
    
    assert len(clips) == 2
    
    # First clip merged c1 and c2 (padded by 1.0)
    # c1: 9.0 to 16.0, c2: 13.0 to 21.0 -> merge: 9.0 to 21.0
    assert clips[0].start_time == 9.0
    assert clips[0].end_time == 21.0
    assert set(clips[0].candidate_ids) == {c1.id, c2.id}
    assert clips[0].score == 20.0  # 2 generators * 10
    
    # Second clip
    # c3: 29.0 to 36.0
    assert clips[1].start_time == 29.0
    assert clips[1].end_time == 36.0
    assert clips[1].candidate_ids == [c3.id]
    assert clips[1].score == 10.0
