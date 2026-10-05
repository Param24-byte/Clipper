"""Jobs router."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.ids import new_id
from src.api.schemas import CreateProbeJobRequest, CreateIngestJobRequest, JobResponse
from src.db import get_db
from src.db.models import JobRow, SourceRow
from src.domain.models import JobStage, JobState
from src.jobs.tasks import probe_source, ingest_source, transcribe_source, build_index, discover_candidates_task, resolve_boundaries_task, rank_clips_task, generate_edl_task, process_video_pipeline
from src.telemetry.logging import get_logger

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = get_logger(__name__)


@router.post(
    "/probe",
    response_model=JobResponse,
    status_code=202,
    summary="Enqueue a probe_source job",
)
async def create_probe_job(
    body: CreateProbeJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    # Validate source belongs to project
    src_result = await db.execute(
        select(SourceRow).where(
            SourceRow.id == body.source_id,
            SourceRow.project_id == body.project_id,
        )
    )
    if src_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Source not found in project")

    # Idempotency: check for an existing non-failed job for this source+stage
    existing = await db.execute(
        select(JobRow).where(
            JobRow.source_id == body.source_id,
            JobRow.stage == JobStage.PROBE_SOURCE,
            JobRow.state.in_([JobState.QUEUED, JobState.RUNNING, JobState.SUCCEEDED]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="A probe job already exists for this source",
        )

    now = datetime.utcnow()
    row = JobRow(
        id=new_id(),
        project_id=body.project_id,
        source_id=body.source_id,
        stage=JobStage.PROBE_SOURCE,
        state=JobState.QUEUED,
        celery_task_id=None,
        input_artifact_ids=[],
        output_artifact_ids=[],
        error_message=None,
        created_at=now,
        updated_at=now,
        extra_metadata={},
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    # Dispatch to Celery
    task = probe_source.delay(job_id=row.id, source_id=body.source_id)
    row.celery_task_id = task.id
    await db.commit()
    await db.refresh(row)

    logger.info("probe_job_enqueued", job_id=row.id, task_id=task.id)
    return JobResponse.model_validate(row)


@router.post(
    "/ingest",
    response_model=JobResponse,
    status_code=202,
    summary="Enqueue an ingest_source job",
)
async def create_ingest_job(
    body: CreateIngestJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    # Validate source belongs to project
    src_result = await db.execute(
        select(SourceRow).where(
            SourceRow.id == body.source_id,
            SourceRow.project_id == body.project_id,
        )
    )
    if src_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Source not found in project")

    # Idempotency: check for an existing non-failed job for this source+stage
    existing = await db.execute(
        select(JobRow).where(
            JobRow.source_id == body.source_id,
            JobRow.stage == JobStage.INGEST,
            JobRow.state.in_([JobState.QUEUED, JobState.RUNNING, JobState.SUCCEEDED]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="An ingest job already exists for this source",
        )

    now = datetime.utcnow()
    row = JobRow(
        id=new_id(),
        project_id=body.project_id,
        source_id=body.source_id,
        stage=JobStage.INGEST,
        state=JobState.QUEUED,
        celery_task_id=None,
        input_artifact_ids=[],
        output_artifact_ids=[],
        error_message=None,
        created_at=now,
        updated_at=now,
        extra_metadata={},
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    # Dispatch to Celery
    task = ingest_source.delay(job_id=row.id, source_id=body.source_id)
    row.celery_task_id = task.id
    await db.commit()
    await db.refresh(row)

    logger.info("ingest_job_enqueued", job_id=row.id, task_id=task.id)
    return JobResponse.model_validate(row)


@router.post(
    "/transcribe",
    response_model=JobResponse,
    status_code=202,
    summary="Enqueue a transcribe_source job",
)
async def create_transcribe_job(
    body: CreateIngestJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    # Validate source belongs to project
    src_result = await db.execute(
        select(SourceRow).where(
            SourceRow.id == body.source_id,
            SourceRow.project_id == body.project_id,
        )
    )
    if src_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Source not found in project")

    # Idempotency
    existing = await db.execute(
        select(JobRow).where(
            JobRow.source_id == body.source_id,
            JobRow.stage == JobStage.TRANSCRIBE,
            JobRow.state.in_([JobState.QUEUED, JobState.RUNNING, JobState.SUCCEEDED]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A transcribe job already exists for this source")

    now = datetime.utcnow()
    row = JobRow(
        id=new_id(),
        project_id=body.project_id,
        source_id=body.source_id,
        stage=JobStage.TRANSCRIBE,
        state=JobState.QUEUED,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    task = transcribe_source.delay(job_id=row.id, source_id=body.source_id)
    row.celery_task_id = task.id
    await db.commit()
    
    return JobResponse.model_validate(row)


@router.post(
    "/index",
    response_model=JobResponse,
    status_code=202,
    summary="Enqueue a build_index job",
)
async def create_index_job(
    body: CreateIngestJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    # Validate source belongs to project
    src_result = await db.execute(
        select(SourceRow).where(
            SourceRow.id == body.source_id,
            SourceRow.project_id == body.project_id,
        )
    )
    if src_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Source not found in project")

    # Idempotency
    existing = await db.execute(
        select(JobRow).where(
            JobRow.source_id == body.source_id,
            JobRow.stage == JobStage.INDEX,
            JobRow.state.in_([JobState.QUEUED, JobState.RUNNING, JobState.SUCCEEDED]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="An index job already exists for this source")

    now = datetime.utcnow()
    row = JobRow(
        id=new_id(),
        project_id=body.project_id,
        source_id=body.source_id,
        stage=JobStage.INDEX,
        state=JobState.QUEUED,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    task = build_index.delay(job_id=row.id, source_id=body.source_id)
    row.celery_task_id = task.id
    await db.commit()
    
    return JobResponse.model_validate(row)


@router.post(
    "/discover",
    response_model=JobResponse,
    status_code=202,
    summary="Enqueue a discover_candidates job",
)
async def create_discover_job(
    body: CreateIngestJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    # Validate source belongs to project
    src_result = await db.execute(
        select(SourceRow).where(
            SourceRow.id == body.source_id,
            SourceRow.project_id == body.project_id,
        )
    )
    if src_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Source not found in project")

    # Idempotency
    existing = await db.execute(
        select(JobRow).where(
            JobRow.source_id == body.source_id,
            JobRow.stage == JobStage.DISCOVER_CANDIDATES,
            JobRow.state.in_([JobState.QUEUED, JobState.RUNNING, JobState.SUCCEEDED]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A discover_candidates job already exists")

    now = datetime.utcnow()
    row = JobRow(
        id=new_id(),
        project_id=body.project_id,
        source_id=body.source_id,
        stage=JobStage.DISCOVER_CANDIDATES,
        state=JobState.QUEUED,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    task = discover_candidates_task.delay(job_id=row.id, source_id=body.source_id)
    row.celery_task_id = task.id
    await db.commit()
    
    return JobResponse.model_validate(row)


@router.post(
    "/resolve",
    response_model=JobResponse,
    status_code=202,
    summary="Enqueue a resolve_boundaries job",
)
async def create_resolve_job(
    body: CreateIngestJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    # Validate source belongs to project
    src_result = await db.execute(
        select(SourceRow).where(
            SourceRow.id == body.source_id,
            SourceRow.project_id == body.project_id,
        )
    )
    if src_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Source not found in project")

    # Idempotency
    existing = await db.execute(
        select(JobRow).where(
            JobRow.source_id == body.source_id,
            JobRow.stage == JobStage.RESOLVE_BOUNDARIES,
            JobRow.state.in_([JobState.QUEUED, JobState.RUNNING, JobState.SUCCEEDED]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A resolve_boundaries job already exists")

    now = datetime.utcnow()
    row = JobRow(
        id=new_id(),
        project_id=body.project_id,
        source_id=body.source_id,
        stage=JobStage.RESOLVE_BOUNDARIES,
        state=JobState.QUEUED,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    task = resolve_boundaries_task.delay(job_id=row.id, source_id=body.source_id)
    row.celery_task_id = task.id
    await db.commit()
    
    return JobResponse.model_validate(row)


@router.post(
    "/rank",
    response_model=JobResponse,
    status_code=202,
    summary="Enqueue a rank_clips job",
)
async def create_rank_job(
    body: CreateIngestJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    # Validate source belongs to project
    src_result = await db.execute(
        select(SourceRow).where(
            SourceRow.id == body.source_id,
            SourceRow.project_id == body.project_id,
        )
    )
    if src_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Source not found in project")

    # Idempotency
    existing = await db.execute(
        select(JobRow).where(
            JobRow.source_id == body.source_id,
            JobRow.stage == JobStage.RANK,
            JobRow.state.in_([JobState.QUEUED, JobState.RUNNING, JobState.SUCCEEDED]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A rank_clips job already exists")

    now = datetime.utcnow()
    row = JobRow(
        id=new_id(),
        project_id=body.project_id,
        source_id=body.source_id,
        stage=JobStage.RANK,
        state=JobState.QUEUED,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    task = rank_clips_task.delay(job_id=row.id, source_id=body.source_id)
    row.celery_task_id = task.id
    await db.commit()
    
    return JobResponse.model_validate(row)


@router.post(
    "/edl",
    response_model=JobResponse,
    status_code=202,
    summary="Enqueue a generate_edl job",
)
async def create_edl_job(
    body: CreateIngestJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    # Validate source belongs to project
    src_result = await db.execute(
        select(SourceRow).where(
            SourceRow.id == body.source_id,
            SourceRow.project_id == body.project_id,
        )
    )
    if src_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Source not found in project")

    # Idempotency
    existing = await db.execute(
        select(JobRow).where(
            JobRow.source_id == body.source_id,
            JobRow.stage == JobStage.GENERATE_EDL,
            JobRow.state.in_([JobState.QUEUED, JobState.RUNNING, JobState.SUCCEEDED]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A generate_edl job already exists")

    now = datetime.utcnow()
    row = JobRow(
        id=new_id(),
        project_id=body.project_id,
        source_id=body.source_id,
        stage=JobStage.GENERATE_EDL,
        state=JobState.QUEUED,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    task = generate_edl_task.delay(job_id=row.id, source_id=body.source_id)
    row.celery_task_id = task.id
    await db.commit()
    
    return JobResponse.model_validate(row)


@router.post(
    "/process",
    response_model=JobResponse,
    status_code=202,
    summary="Enqueue a full end-to-end processing pipeline",
)
async def create_process_job(
    body: CreateIngestJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    # Validate source belongs to project
    src_result = await db.execute(
        select(SourceRow).where(
            SourceRow.id == body.source_id,
            SourceRow.project_id == body.project_id,
        )
    )
    if src_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Source not found in project")

    now = datetime.utcnow()
    # Use PIPELINE stage to track the overall chain
    row = JobRow(
        id=new_id(),
        project_id=body.project_id,
        source_id=body.source_id,
        stage="pipeline",
        state=JobState.QUEUED,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    task = process_video_pipeline.delay(job_id=row.id, source_id=body.source_id)
    row.celery_task_id = task.id
    await db.commit()
    
    return JobResponse.model_validate(row)


@router.get("/{job_id}", response_model=JobResponse, summary="Get job status")
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    result = await db.execute(select(JobRow).where(JobRow.id == job_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(row)
