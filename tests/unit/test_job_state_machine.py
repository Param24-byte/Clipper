"""Unit tests for the Job domain state machine."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.domain.models import Job, JobStage, JobState


def _make_job(state: JobState = JobState.QUEUED) -> Job:
    return Job(
        id="01J123456789ABCDEFGHJKMNPQ",
        project_id="01J123456789ABCDEFGHJKMNPR",
        source_id=None,
        stage=JobStage.PROBE_SOURCE,
        state=state,
        celery_task_id=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def test_queued_can_transition_to_running():
    job = _make_job(JobState.QUEUED)
    job.transition_to(JobState.RUNNING)
    assert job.state == JobState.RUNNING
    assert job.started_at is not None


def test_running_can_transition_to_succeeded():
    job = _make_job(JobState.RUNNING)
    job.transition_to(JobState.SUCCEEDED)
    assert job.state == JobState.SUCCEEDED
    assert job.finished_at is not None


def test_running_can_transition_to_failed():
    job = _make_job(JobState.RUNNING)
    job.transition_to(JobState.FAILED)
    assert job.state == JobState.FAILED


def test_failed_can_retry_to_queued():
    job = _make_job(JobState.FAILED)
    job.transition_to(JobState.QUEUED)
    assert job.state == JobState.QUEUED


def test_succeeded_cannot_transition():
    job = _make_job(JobState.SUCCEEDED)
    with pytest.raises(ValueError, match="Invalid transition"):
        job.transition_to(JobState.RUNNING)


def test_queued_cannot_skip_to_succeeded():
    job = _make_job(JobState.QUEUED)
    with pytest.raises(ValueError, match="Invalid transition"):
        job.transition_to(JobState.SUCCEEDED)


def test_can_transition_to_returns_bool():
    job = _make_job(JobState.QUEUED)
    assert job.can_transition_to(JobState.RUNNING) is True
    assert job.can_transition_to(JobState.SUCCEEDED) is False
