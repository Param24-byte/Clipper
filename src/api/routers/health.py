"""Health router — used by Docker and load-balancer probes."""

from __future__ import annotations

from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import text

from src.api.schemas import HealthResponse
from src.config import get_settings
from src.db import get_engine

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Service health check")
async def health() -> HealthResponse:
    settings = get_settings()
    checks: dict[str, str] = {}

    # ── DB check ──────────────────────────────────────────────────────────────
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    # ── Redis check ───────────────────────────────────────────────────────────
    try:
        redis = Redis.from_url(settings.redis_url)
        await redis.ping()
        await redis.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"

    return HealthResponse(
        status=overall,
        version="0.0.1",
        checks=checks,
    )
