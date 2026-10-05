"""initial schema — version 0

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-04

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums ─────────────────────────────────────────────────────────────────
    project_status = sa.Enum(
        "created", "analyzing", "ready", "error", name="project_status"
    )
    source_type = sa.Enum("youtube", "upload", "twitch_vod", name="source_type")
    job_state = sa.Enum(
        "queued", "running", "succeeded", "failed", "cancelled", name="job_state"
    )
    job_stage = sa.Enum(
        "probe_source",
        "ingest",
        "normalize",
        "transcribe",
        "index",
        "discover_candidates",
        "resolve_boundaries",
        "rank",
        "generate_edl",
        "render_preview",
        "render_final",
        name="job_stage",
    )

    # ── projects ──────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("owner_id", sa.String(26), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", project_status, nullable=False, server_default="created"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("metadata", sa.JSON, nullable=False, server_default="{}"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])

    # ── sources ───────────────────────────────────────────────────────────────
    op.create_table(
        "sources",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(26),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", source_type, nullable=False),
        sa.Column("uri", sa.Text, nullable=False),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column("fps", sa.Float, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_sources_project_id", "sources", ["project_id"])

    # ── artifacts ─────────────────────────────────────────────────────────────
    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column(
            "source_id",
            sa.String(26),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("storage_uri", sa.Text, nullable=False),
        sa.Column("metadata", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_artifacts_source_id", "artifacts", ["source_id"])
    op.create_index(
        "ix_artifacts_source_stage_version",
        "artifacts",
        ["source_id", "stage", "version"],
    )

    # ── jobs ──────────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(26),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.String(26),
            sa.ForeignKey("sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("stage", job_stage, nullable=False),
        sa.Column("state", job_state, nullable=False, server_default="queued"),
        sa.Column("celery_task_id", sa.String(64), nullable=True),
        sa.Column("input_artifact_ids", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("output_artifact_ids", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=False, server_default="{}"),
    )
    op.create_index("ix_jobs_project_id", "jobs", ["project_id"])
    op.create_index("ix_jobs_source_id", "jobs", ["source_id"])
    op.create_index("ix_jobs_state", "jobs", ["state"])


def downgrade() -> None:
    op.drop_table("jobs")
    op.drop_table("artifacts")
    op.drop_table("sources")
    op.drop_table("projects")

    for enum_name in ("job_stage", "job_state", "source_type", "project_status"):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
