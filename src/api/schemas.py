"""
Pydantic request/response schemas for the API layer.

These are NOT the domain models. They are the wire-format contracts.
Validation happens here; business logic stays in domain/db layers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


# ── Projects ──────────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    owner_id: str = Field(..., min_length=1, max_length=26)
    name: str = Field(..., min_length=1, max_length=255)


class ProjectResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Sources ───────────────────────────────────────────────────────────────────

class CreateSourceRequest(BaseModel):
    project_id: str = Field(..., min_length=1, max_length=26)
    type: str = Field(..., pattern="^(youtube|upload)$")
    uri: str = Field(..., min_length=1, max_length=2048)


class SourceResponse(BaseModel):
    id: str
    project_id: str
    type: str
    uri: str
    checksum: str | None
    duration_seconds: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Jobs ──────────────────────────────────────────────────────────────────────

class CreateProbeJobRequest(BaseModel):
    project_id: str = Field(..., min_length=1, max_length=26)
    source_id: str = Field(..., min_length=1, max_length=26)


class CreateIngestJobRequest(BaseModel):
    project_id: str = Field(..., min_length=1, max_length=26)
    source_id: str = Field(..., min_length=1, max_length=26)


class JobResponse(BaseModel):
    id: str
    project_id: str
    source_id: str | None
    stage: str
    state: str
    celery_task_id: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    checks: dict[str, str]
