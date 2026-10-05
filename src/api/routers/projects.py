"""Projects router."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.ids import new_id
from src.api.schemas import CreateProjectRequest, ProjectResponse
from src.db import get_db
from src.db.models import ProjectRow
from src.domain.models import ProjectStatus
from src.telemetry.logging import get_logger

router = APIRouter(prefix="/projects", tags=["projects"])
logger = get_logger(__name__)


@router.post("", response_model=ProjectResponse, status_code=201, summary="Create a project")
async def create_project(
    body: CreateProjectRequest,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    now = datetime.utcnow()
    row = ProjectRow(
        id=new_id(),
        owner_id=body.owner_id,
        name=body.name,
        status=ProjectStatus.CREATED,
        created_at=now,
        updated_at=now,
        extra_metadata={},
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    logger.info("project_created", project_id=row.id, owner_id=row.owner_id)
    return ProjectResponse.model_validate(row)


@router.get("/{project_id}", response_model=ProjectResponse, summary="Get a project")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    result = await db.execute(select(ProjectRow).where(ProjectRow.id == project_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(row)
