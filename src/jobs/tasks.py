"""
Celery tasks — Version 0.

Only probe_source is implemented here as the sentinel test task.
Real pipeline stages (ingest, transcribe, …) are added in later versions.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

from celery import chain
from sqlalchemy.future import select

from src.db.base import get_session_factory
from src.db.models import JobRow, SourceRow
from src.jobs.celery_app import celery_app
from src.media.ingest.pipeline import run_ingest
from src.intelligence.transcript.pipeline import run_transcription
from src.intelligence.index.builder import build_media_index
from src.intelligence.candidates.pipeline import discover_candidates
from src.intelligence.boundaries.resolver import resolve_boundaries
from src.intelligence.ranking.ranker import rank_clips
from src.export.edl_generator import generate_edl
from src.storage import get_artifact_store
from src.telemetry.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="jobs.probe_source",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def probe_source(self, job_id: str, source_id: str) -> dict:
    """
    Stage: probe_source
    -
    Version 0 stub — confirms the job machinery works end-to-end.
    In Version 0.1 this will run FFprobe against the source media.

    Returns a minimal result dict that the API can store as an artifact.
    """
    logger.info("probe_source_started", job_id=job_id, source_id=source_id, task_id=self.request.id)

    try:
        # ── TODO (Version 0.1): run FFprobe here ─────────────────────────────
        result = {
            "job_id": job_id,
            "source_id": source_id,
            "stage": "probe_source",
            "stage_version": "v0",
            "status": "succeeded",
            "probed_at": datetime.utcnow().isoformat(),
            "note": "stub — real FFprobe call added in Version 0.1",
        }
        logger.info("probe_source_succeeded", job_id=job_id, source_id=source_id)
        return result

    except Exception as exc:
        logger.error("probe_source_failed", job_id=job_id, source_id=source_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="jobs.ingest_source",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def ingest_source(self, job_id: str, source_id: str) -> dict:
    """
    Stage: ingest
    -
    Downloads media, probes, extracts audio, generates proxy.
    """
    logger.info("ingest_source_started", job_id=job_id, source_id=source_id, task_id=self.request.id)

    async def _run():
        factory = get_session_factory()
        store = get_artifact_store()
        async with factory() as db:
            # Get source URI and type
            result = await db.execute(select(SourceRow).where(SourceRow.id == source_id))
            source_row = result.scalar_one_or_none()
            if not source_row:
                raise ValueError(f"Source not found: {source_id}")
            
            uri = source_row.uri
            source_type = source_row.type
            
            # Run pipeline
            artifacts = await run_ingest(source_id, uri, source_type, store, db)
            return [a.id for a in artifacts]

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        artifact_ids = loop.run_until_complete(_run())
        result = {
            "job_id": job_id,
            "source_id": source_id,
            "stage": "ingest",
            "stage_version": "v1",
            "status": "succeeded",
            "output_artifact_ids": artifact_ids,
        }
        logger.info("ingest_source_succeeded", job_id=job_id, source_id=source_id)
        return result
    except Exception as exc:
        logger.error("ingest_source_failed", job_id=job_id, source_id=source_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="jobs.transcribe_source",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def transcribe_source(self, job_id: str, source_id: str) -> dict:
    """Stage: transcribe"""
    logger.info("transcribe_source_started", job_id=job_id, source_id=source_id, task_id=self.request.id)

    async def _run():
        factory = get_session_factory()
        store = get_artifact_store()
        async with factory() as db:
            artifact = await run_transcription(source_id, store, db)
            return [artifact.id]

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        artifact_ids = loop.run_until_complete(_run())
        result = {
            "job_id": job_id,
            "source_id": source_id,
            "stage": "transcribe",
            "stage_version": "v1",
            "status": "succeeded",
            "output_artifact_ids": artifact_ids,
        }
        logger.info("transcribe_source_succeeded", job_id=job_id, source_id=source_id)
        return result
    except Exception as exc:
        logger.error("transcribe_source_failed", job_id=job_id, source_id=source_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="jobs.build_index",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def build_index(self, job_id: str, source_id: str) -> dict:
    """Stage: index"""
    logger.info("build_index_started", job_id=job_id, source_id=source_id, task_id=self.request.id)

    async def _run():
        factory = get_session_factory()
        store = get_artifact_store()
        async with factory() as db:
            artifact = await build_media_index(source_id, store, db)
            return [artifact.id]

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        artifact_ids = loop.run_until_complete(_run())
        result = {
            "job_id": job_id,
            "source_id": source_id,
            "stage": "index",
            "stage_version": "v1",
            "status": "succeeded",
            "output_artifact_ids": artifact_ids,
        }
        logger.info("build_index_succeeded", job_id=job_id, source_id=source_id)
        return result
    except Exception as exc:
        logger.error("build_index_failed", job_id=job_id, source_id=source_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="jobs.discover_candidates",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def discover_candidates_task(self, job_id: str, source_id: str) -> dict:
    """Stage: discover_candidates"""
    logger.info("discover_candidates_started", job_id=job_id, source_id=source_id, task_id=self.request.id)

    async def _run():
        factory = get_session_factory()
        store = get_artifact_store()
        async with factory() as db:
            candidate_ids = await discover_candidates(source_id, store, db)
            return candidate_ids

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        candidate_ids = loop.run_until_complete(_run())
        result = {
            "job_id": job_id,
            "source_id": source_id,
            "stage": "discover_candidates",
            "stage_version": "v1",
            "status": "succeeded",
            "metadata": {"candidate_ids": candidate_ids}
        }
        logger.info("discover_candidates_succeeded", job_id=job_id, source_id=source_id)
        return result
    except Exception as exc:
        logger.error("discover_candidates_failed", job_id=job_id, source_id=source_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="jobs.resolve_boundaries",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def resolve_boundaries_task(self, job_id: str, source_id: str) -> dict:
    """Stage: resolve_boundaries"""
    logger.info("resolve_boundaries_started", job_id=job_id, source_id=source_id, task_id=self.request.id)

    async def _run():
        factory = get_session_factory()
        async with factory() as db:
            clip_ids = await resolve_boundaries(source_id, db)
            return clip_ids

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        clip_ids = loop.run_until_complete(_run())
        result = {
            "job_id": job_id,
            "source_id": source_id,
            "stage": "resolve_boundaries",
            "stage_version": "v1",
            "status": "succeeded",
            "metadata": {"clip_ids": clip_ids}
        }
        logger.info("resolve_boundaries_succeeded", job_id=job_id, source_id=source_id)
        return result
    except Exception as exc:
        logger.error("resolve_boundaries_failed", job_id=job_id, source_id=source_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="jobs.rank_clips",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def rank_clips_task(self, job_id: str, source_id: str) -> dict:
    """Stage: rank"""
    logger.info("rank_clips_started", job_id=job_id, source_id=source_id, task_id=self.request.id)

    async def _run():
        factory = get_session_factory()
        async with factory() as db:
            selected_ids = await rank_clips(source_id, db)
            return selected_ids

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        selected_ids = loop.run_until_complete(_run())
        result = {
            "job_id": job_id,
            "source_id": source_id,
            "stage": "rank",
            "stage_version": "v1",
            "status": "succeeded",
            "metadata": {"selected_clip_ids": selected_ids}
        }
        logger.info("rank_clips_succeeded", job_id=job_id, source_id=source_id)
        return result
    except Exception as exc:
        logger.error("rank_clips_failed", job_id=job_id, source_id=source_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="jobs.generate_edl",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def generate_edl_task(self, job_id: str, source_id: str) -> dict:
    """Stage: generate_edl"""
    logger.info("generate_edl_started", job_id=job_id, source_id=source_id, task_id=self.request.id)

    async def _run():
        factory = get_session_factory()
        store = get_artifact_store()
        async with factory() as db:
            artifact = await generate_edl(source_id, store, db)
            return {"artifact_uri": artifact.storage_uri}

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        result_meta = loop.run_until_complete(_run())
        result = {
            "job_id": job_id,
            "source_id": source_id,
            "stage": "generate_edl",
            "stage_version": "v1",
            "status": "succeeded",
            "metadata": result_meta
        }
        logger.info("generate_edl_succeeded", job_id=job_id, source_id=source_id)
        return result
    except Exception as exc:
        logger.error("generate_edl_failed", job_id=job_id, source_id=source_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="jobs.process_video_pipeline",
    bind=True,
    max_retries=1,
)
def process_video_pipeline(self, job_id: str, source_id: str) -> dict:
    """
    Master orchestrator task that chains the entire pipeline for a source.
    Note: A real-world pipeline might use Celery Canvas (chain/chord) more explicitly, 
    but for simplicity we'll enqueue the individual tasks sequentially or just call 
    their internal sync functions. To truly leverage Celery concurrency and retries on 
    each step, we create a Celery chain.
    """
    logger.info("pipeline_started", job_id=job_id, source_id=source_id)
    
    # Using celery signature chain
    pipeline_chain = chain(
        probe_source.s(job_id, source_id),
        ingest_source.s(job_id, source_id),
        transcribe_source.s(job_id, source_id),
        build_index.s(job_id, source_id),
        discover_candidates_task.s(job_id, source_id),
        resolve_boundaries_task.s(job_id, source_id),
        rank_clips_task.s(job_id, source_id),
        generate_edl_task.s(job_id, source_id)
    )
    
    result = pipeline_chain.apply_async()
    return {"chain_id": result.id, "status": "dispatched"}


