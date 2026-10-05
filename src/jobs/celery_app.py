"""
Celery application instance.

Import `celery_app` whenever you need to register or dispatch tasks.
"""

from __future__ import annotations

from celery import Celery

from src.config import get_settings


def create_celery_app() -> Celery:
    settings = get_settings()
    app = Celery(
        "clipper",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=["src.jobs.tasks"],
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        # Each stage is a short-lived retryable unit; no mega-timeout
        task_soft_time_limit=3600,
        task_time_limit=3660,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )
    return app


celery_app = create_celery_app()
