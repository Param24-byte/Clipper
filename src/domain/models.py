"""
Domain models — pure Python, no framework dependency.

These are the authoritative typed contracts for every core concept.
DB-mapped variants live in src/db/models.py but must mirror these fields.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ── Job States ────────────────────────────────────────────────────────────────

class JobState(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Job Stages ────────────────────────────────────────────────────────────────

class JobStage(str, enum.Enum):
    PROBE_SOURCE = "probe_source"
    INGEST = "ingest"
    NORMALIZE = "normalize"
    TRANSCRIBE = "transcribe"
    INDEX = "index"
    DISCOVER_CANDIDATES = "discover_candidates"
    RESOLVE_BOUNDARIES = "resolve_boundaries"
    RANK = "rank"
    GENERATE_EDL = "generate_edl"
    RENDER_PREVIEW = "render_preview"
    RENDER_FINAL = "render_final"


# ── Source Type ───────────────────────────────────────────────────────────────

class SourceType(str, enum.Enum):
    YOUTUBE = "youtube"
    UPLOAD = "upload"
    TWITCH_VOD = "twitch_vod"  # Future


# ── Project Status ────────────────────────────────────────────────────────────

class ProjectStatus(str, enum.Enum):
    CREATED = "created"
    ANALYZING = "analyzing"
    READY = "ready"
    ERROR = "error"


# ── Domain dataclasses ────────────────────────────────────────────────────────

@dataclass
class Project:
    """One creator workflow/session."""

    id: str
    owner_id: str
    name: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Source:
    """Original long-form media input."""

    id: str
    project_id: str
    type: SourceType
    uri: str
    checksum: str | None
    duration_seconds: float | None
    width: int | None
    height: int | None
    fps: float | None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Artifact:
    """Any derived, cacheable output produced by a pipeline stage."""

    id: str
    source_id: str
    stage: str
    version: str
    content_hash: str | None
    storage_uri: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def cache_key(self) -> str:
        """Deterministic key for cache/dedup lookups."""
        return f"{self.source_id}:{self.stage}:{self.version}:{self.content_hash or 'nohash'}"


@dataclass
class Job:
    """Represents one unit of pipeline work."""

    id: str
    project_id: str
    source_id: str | None
    stage: JobStage
    state: JobState
    celery_task_id: str | None
    # Artifact versions this job consumed as input
    input_artifact_ids: list[str] = field(default_factory=list)
    # Artifact versions this job produced as output
    output_artifact_ids: list[str] = field(default_factory=list)
    error_message: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # ── Allowed state transitions ─────────────────────────────────────────────

    _TRANSITIONS: dict[JobState, frozenset[JobState]] = field(
        default_factory=lambda: {
            JobState.QUEUED: frozenset({JobState.RUNNING, JobState.CANCELLED}),
            JobState.RUNNING: frozenset({JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED}),
            JobState.SUCCEEDED: frozenset(),
            JobState.FAILED: frozenset({JobState.QUEUED}),   # allow retry
            JobState.CANCELLED: frozenset({JobState.QUEUED}),  # allow re-queue
        },
        init=False,
        repr=False,
    )

    def can_transition_to(self, new_state: JobState) -> bool:
        return new_state in self._TRANSITIONS.get(self.state, frozenset())

    def transition_to(self, new_state: JobState) -> None:
        if not self.can_transition_to(new_state):
            raise ValueError(
                f"Invalid transition for job {self.id}: {self.state} → {new_state}"
            )
        self.state = new_state
        self.updated_at = datetime.utcnow()
        if new_state == JobState.RUNNING:
            self.started_at = datetime.utcnow()
        if new_state in (JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED):
            self.finished_at = datetime.utcnow()


@dataclass
class Candidate:
    """A potentially interesting moment identified by a generator."""
    
    id: str
    source_id: str
    event_start: float
    event_end: float
    generators: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Clip:
    """A resolved, non-overlapping editorial segment."""
    
    id: str
    source_id: str
    project_id: str
    start_time: float
    end_time: float
    candidate_ids: list[str] = field(default_factory=list)
    score: float = 0.0
    status: str = "draft"
    created_at: datetime = field(default_factory=datetime.utcnow)
