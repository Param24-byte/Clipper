"""
SQLAlchemy ORM models.

These mirror the domain dataclasses in src/domain/models.py.
Never add business logic here — that belongs in the domain layer.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base
from src.domain.models import JobStage, JobState, ProjectStatus, SourceType


class ProjectRow(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(26), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(ProjectStatus, name="project_status"), nullable=False, default=ProjectStatus.CREATED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    sources: Mapped[list[SourceRow]] = relationship("SourceRow", back_populates="project")
    jobs: Mapped[list[JobRow]] = relationship("JobRow", back_populates="project")


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        Enum(SourceType, name="source_type"), nullable=False
    )
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)
    width: Mapped[int | None] = mapped_column(nullable=True)
    height: Mapped[int | None] = mapped_column(nullable=True)
    fps: Mapped[float | None] = mapped_column(nullable=True)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    project: Mapped[ProjectRow] = relationship("ProjectRow", back_populates="sources")
    artifacts: Mapped[list[ArtifactRow]] = relationship("ArtifactRow", back_populates="source")
    jobs: Mapped[list[JobRow]] = relationship("JobRow", back_populates="source")


class ArtifactRow(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    source: Mapped[SourceRow] = relationship("SourceRow", back_populates="artifacts")


class JobRow(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    stage: Mapped[str] = mapped_column(
        Enum(JobStage, name="job_stage"), nullable=False
    )
    state: Mapped[str] = mapped_column(
        Enum(JobState, name="job_state"), nullable=False, default=JobState.QUEUED
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_artifact_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    output_artifact_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    project: Mapped[ProjectRow] = relationship("ProjectRow", back_populates="jobs")
    source: Mapped[SourceRow | None] = relationship("SourceRow", back_populates="jobs")


class CandidateRow(Base):
    __tablename__ = "candidates"
    
    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_start: Mapped[float] = mapped_column(nullable=False)
    event_end: Mapped[float] = mapped_column(nullable=False)
    generators: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    source: Mapped[SourceRow] = relationship("SourceRow")


class ClipRow(Base):
    __tablename__ = "clips"
    
    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_time: Mapped[float] = mapped_column(nullable=False)
    end_time: Mapped[float] = mapped_column(nullable=False)
    candidate_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    source: Mapped[SourceRow] = relationship("SourceRow")
    project: Mapped[ProjectRow] = relationship("ProjectRow")
