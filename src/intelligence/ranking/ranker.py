"""Score and filter clips down to the best subset."""

from __future__ import annotations

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.db.models import ClipRow
from src.telemetry.logging import get_logger

logger = get_logger(__name__)


async def rank_clips(
    source_id: str,
    db: AsyncSession,
    top_n: int = 5
) -> List[str]:
    """
    Ranks clips and selects the top N.
    Updates the status of selected clips to 'selected' and others to 'rejected'.
    Returns the IDs of the selected clips.
    """
    logger.info("rank_clips_started", source_id=source_id)
    
    result = await db.execute(select(ClipRow).where(ClipRow.source_id == source_id))
    clips = result.scalars().all()
    
    if not clips:
        logger.warning("no_clips_found_for_ranking", source_id=source_id)
        return []

    # Sort clips by score descending
    sorted_clips = sorted(clips, key=lambda c: c.score, reverse=True)
    
    selected_ids = []
    
    for i, clip in enumerate(sorted_clips):
        if i < top_n:
            clip.status = "selected"
            selected_ids.append(clip.id)
        else:
            clip.status = "rejected"
            
    await db.commit()
    logger.info("rank_clips_completed", source_id=source_id, selected_count=len(selected_ids))
    return selected_ids
