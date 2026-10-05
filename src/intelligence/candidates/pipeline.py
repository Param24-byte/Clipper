"""Candidate discovery orchestration."""

from __future__ import annotations

import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.db.models import ArtifactRow, CandidateRow
from src.intelligence.candidates.semantic import SemanticStrongStatement
from src.intelligence.candidates.audio import HighEnergySpike
from src.intelligence.candidates.merger import merge_candidates
from src.storage.base import ArtifactStore
from src.telemetry.logging import get_logger

logger = get_logger(__name__)


async def discover_candidates(
    source_id: str,
    store: ArtifactStore,
    db: AsyncSession,
) -> list[str]:
    """
    Run candidate generators against the media index.
    Returns a list of generated Candidate IDs.
    """
    logger.info("discover_candidates_started", source_id=source_id)

    # 1. Fetch index artifact
    result = await db.execute(
        select(ArtifactRow).where(
            ArtifactRow.source_id == source_id,
            ArtifactRow.stage == "index"
        )
    )
    # Using python filtering to avoid JSON column DB dialects issues
    index_art = next((a for a in result.scalars() if a.extra_metadata.get("filename") == "media_index.json"), None)
    if not index_art:
        raise ValueError(f"No media_index.json artifact found for source {source_id}")

    # 2. Check if we already have candidates for this source_id (idempotency)
    # For a real pipeline, we'd hash the index to know if we need to rerun.
    # For now, if we have candidates for this source, we assume it's done.
    existing = await db.execute(select(CandidateRow).where(CandidateRow.source_id == source_id))
    existing_rows = existing.scalars().all()
    if existing_rows:
        logger.info("discover_candidates_cached", source_id=source_id, count=len(existing_rows))
        return [c.id for c in existing_rows]

    # 3. Download and load index data
    index_data_bytes = await store.get(index_art.storage_uri.replace("local://", ""))
    index_data = json.loads(index_data_bytes)

    # 4. Initialize generators
    generators = [
        SemanticStrongStatement(),
        HighEnergySpike(),
    ]

    # 5. Run generators
    all_candidates = []
    for gen in generators:
        logger.info("running_generator", name=gen.name)
        cands = await gen.generate(source_id, index_data)
        all_candidates.extend(cands)

    # 6. Merge overlapping
    merged_candidates = merge_candidates(all_candidates)
    
    # 7. Persist to DB
    ids = []
    for c in merged_candidates:
        row = CandidateRow(
            id=c.id,
            source_id=c.source_id,
            event_start=c.event_start,
            event_end=c.event_end,
            generators=c.generators,
            reason_codes=c.reason_codes,
            evidence=c.evidence,
            created_at=c.created_at
        )
        db.add(row)
        ids.append(c.id)
        
    await db.commit()
    logger.info("discover_candidates_completed", source_id=source_id, count=len(ids))
    return ids
