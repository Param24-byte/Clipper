"""
FastAPI application factory.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import health, jobs, projects, sources
from src.config import get_settings
from src.telemetry import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.app_log_level)
    logger = get_logger(__name__)
    logger.info("api_starting", env=settings.app_env, version="0.0.1")
    yield
    logger.info("api_stopping")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AI Editorial Clipper API",
        description="Long-form → short-form AI content engine",
        version="0.0.1",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(projects.router)
    app.include_router(sources.router)
    app.include_router(jobs.router)

    return app


app = create_app()
