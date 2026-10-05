"""Sources router."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.ids import new_id
from src.api.schemas import CreateSourceRequest, SourceResponse
from src.db import get_db
from src.db.models import ProjectRow, SourceRow
from src.domain.models import SourceType
from src.telemetry.logging import get_logger

router = APIRouter(prefix="/sources", tags=["sources"])
logger = get_logger(__name__)


@router.post("", response_model=SourceResponse, status_code=201, summary="Register a source")
async def create_source(
    body: CreateSourceRequest,
    db: AsyncSession = Depends(get_db),
) -> SourceResponse:
    # Validate project exists
    proj = await db.execute(select(ProjectRow).where(ProjectRow.id == body.project_id))
    if proj.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Project not found")

    row = SourceRow(
        id=new_id(),
        project_id=body.project_id,
        type=SourceType(body.type),
        uri=body.uri,
        checksum=None,
        duration_seconds=None,
        width=None,
        height=None,
        fps=None,
        extra_metadata={},
        created_at=datetime.utcnow(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    logger.info("source_created", source_id=row.id, project_id=row.project_id, type=row.type)
    return SourceResponse.model_validate(row)


@router.get("/{source_id}", response_model=SourceResponse, summary="Get a source")
async def get_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
) -> SourceResponse:
    result = await db.execute(select(SourceRow).where(SourceRow.id == source_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return SourceResponse.model_validate(row)
