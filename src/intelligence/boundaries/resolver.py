"""Resolves raw candidates into editorial clips."""

from __future__ import annotations

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.ids import new_id
from src.db.models import CandidateRow, ClipRow, SourceRow
from src.telemetry.logging import get_logger

logger = get_logger(__name__)


async def resolve_boundaries(
    source_id: str,
    db: AsyncSession,
) -> List[str]:
    """
    Takes overlapping candidates for a source and merges/snaps them into clean Clips.
    Returns the IDs of the generated Clips.
    """
    logger.info("resolve_boundaries_started", source_id=source_id)
    
    # 1. Fetch Source to get project_id
    src_res = await db.execute(select(SourceRow).where(SourceRow.id == source_id))
    source = src_res.scalar_one_or_none()
    if not source:
        raise ValueError(f"Source {source_id} not found")
        
    # 2. Check idempotency (have we already created clips for this source?)
    existing = await db.execute(select(ClipRow).where(ClipRow.source_id == source_id))
    existing_rows = existing.scalars().all()
    if existing_rows:
        logger.info("resolve_boundaries_cached", source_id=source_id, count=len(existing_rows))
        return [c.id for c in existing_rows]
        
    # 3. Fetch candidates
    result = await db.execute(select(CandidateRow).where(CandidateRow.source_id == source_id))
    candidates = result.scalars().all()
    
    if not candidates:
        logger.warning("no_candidates_found", source_id=source_id)
        return []

    # Simple resolution logic: 
    # The discovery merger already merges highly overlapping ones, 
    # so we just take each candidate and pad it slightly to make a "Clip", 
    # combining their scores.
    # A real resolver might snap to sentence boundaries or scene boundaries.
    
    # Sort by start time
    sorted_cands = sorted(candidates, key=lambda c: c.event_start)
    
    clips = []
    padding = 1.0 # 1 second padding on each side
    
    for cand in sorted_cands:
        start_time = max(0.0, cand.event_start - padding)
        end_time = cand.event_end + padding
        
        # Calculate a naive score based on number of generators
        score = len(cand.generators) * 10.0
        
        clips.append(ClipRow(
            id=new_id(),
            source_id=source_id,
            project_id=source.project_id,
            start_time=start_time,
            end_time=end_time,
            candidate_ids=[cand.id],
            score=score,
            status="draft"
        ))
        
    # Merge overlapping clips
    merged_clips = []
    if clips:
        merged_clips.append(clips[0])
        for current in clips[1:]:
            last = merged_clips[-1]
            if current.start_time <= last.end_time:
                # Merge
                last.end_time = max(last.end_time, current.end_time)
                last.candidate_ids.extend(current.candidate_ids)
                last.score += current.score
            else:
                merged_clips.append(current)

    clip_ids = []
    for c in merged_clips:
        db.add(c)
        clip_ids.append(c.id)
        
    await db.commit()
    
    logger.info("resolve_boundaries_completed", source_id=source_id, count=len(clip_ids))
    return clip_ids
