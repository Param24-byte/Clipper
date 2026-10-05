"""EDL (Edit Decision List) generator."""

from __future__ import annotations

import tempfile
from typing import List
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.ids import new_id
from src.db.models import ClipRow, ArtifactRow
from src.storage.base import ArtifactStore
from src.telemetry.logging import get_logger

logger = get_logger(__name__)


def format_timecode(seconds: float, fps: float = 30.0) -> str:
    """Convert seconds to HH:MM:SS:FF timecode."""
    total_frames = int(round(seconds * fps))
    frames = total_frames % int(fps)
    s = (total_frames // int(fps)) % 60
    m = (total_frames // (int(fps) * 60)) % 60
    h = (total_frames // (int(fps) * 3600))
    return f"{h:02d}:{m:02d}:{s:02d}:{frames:02d}"


async def generate_edl(
    source_id: str,
    store: ArtifactStore,
    db: AsyncSession,
) -> ArtifactRow:
    """
    Finds all 'selected' clips and generates a CMX3600 EDL file.
    Returns the EDL ArtifactRow.
    """
    logger.info("generate_edl_started", source_id=source_id)
    
    # 1. Fetch selected clips
    res = await db.execute(
        select(ClipRow)
        .where(ClipRow.source_id == source_id, ClipRow.status == "selected")
        .order_by(ClipRow.start_time)
    )
    clips = res.scalars().all()
    
    if not clips:
        logger.warning("no_selected_clips_for_edl", source_id=source_id)
        # We can just return empty EDL or raise. We'll generate an empty one.
        
    # 2. Check idempotency (we hash the clip IDs)
    version = "v1"
    stage = "generate_edl"
    import hashlib
    clip_id_str = "".join(sorted([c.id for c in clips]))
    content_hash = hashlib.md5(clip_id_str.encode()).hexdigest()
    
    existing = await db.execute(
        select(ArtifactRow).where(
            ArtifactRow.source_id == source_id,
            ArtifactRow.stage == stage,
            ArtifactRow.version == version,
            ArtifactRow.content_hash == content_hash
        )
    )
    existing_art = existing.scalar_one_or_none()
    if existing_art:
        logger.info("generate_edl_cached", source_id=source_id)
        return existing_art
        
    # 3. Generate EDL content (CMX3600)
    lines = ["TITLE: CLIPPER EXPORT"]
    lines.append("FCM: NON-DROP FRAME")
    
    record_start = 0.0
    for i, clip in enumerate(clips):
        # EDL event number
        event_num = f"{i+1:03d}"
        
        # Source timecodes
        src_in = format_timecode(clip.start_time)
        src_out = format_timecode(clip.end_time)
        
        # Record timecodes (timeline)
        duration = clip.end_time - clip.start_time
        rec_in = format_timecode(record_start)
        record_start += duration
        rec_out = format_timecode(record_start)
        
        # AX V C
        lines.append(f"{event_num}  AX       V     C        {src_in} {src_out} {rec_in} {rec_out}")
        # Audio track 1
        lines.append(f"{event_num}  AX       A     C        {src_in} {src_out} {rec_in} {rec_out}")
        
    edl_text = "\n".join(lines) + "\n"
    
    # 4. Store Artifact
    cache_key = f"{stage}/{source_id}/{version}/{content_hash}/export.edl"
    uri_store = await store.put(cache_key, edl_text.encode("utf-8"), content_type="text/plain")
    
    art_row = ArtifactRow(
        id=new_id(),
        source_id=source_id,
        stage=stage,
        version=version,
        content_hash=content_hash,
        storage_uri=uri_store,
        extra_metadata={"filename": "export.edl"}
    )
    db.add(art_row)
    await db.commit()
    
    logger.info("generate_edl_completed", source_id=source_id, num_events=len(clips))
    return art_row
