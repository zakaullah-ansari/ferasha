"""Ferasha AI engine - FastAPI application.

Responsibilities are deliberately narrow: this service detects and blurs
faces, and reports what it did. It owns no customer data, issues no
credentials, and performs no Django migrations (D2 - Django owns the schema).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import routes_media
from app.core.config import get_settings
from app.services.face_blur import detector

logging.basicConfig(
    level=get_settings().log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models once at startup, not per request.

    Building a MediaPipe graph costs hundreds of milliseconds and leaks
    memory if repeated per request. Phase 3 exit criteria require this be
    measurable, so the loaded state is exposed on /ready.
    """
    settings = get_settings()
    logger.info("Starting %s", settings.service_name)
    detector.load()
    try:
        yield
    finally:
        detector.close()
        logger.info("Stopped %s", settings.service_name)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Ferasha AI Engine",
        description=(
            "Privacy processing for vendor imagery. Every image with a "
            "detectable face is irreversibly blurred before it can be served."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    app.add_middleware(
        CORSMiddleware,
        # The engine is an internal service; browsers never call it directly.
        allow_origins=[],
        allow_credentials=False,
        allow_methods=["POST", "GET"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(routes_media.router, prefix="/api/v1")

    @app.get("/health", tags=["ops"], summary="Liveness probe")
    async def health() -> dict:
        return {"status": "ok", "service": settings.service_name}

    @app.get("/ready", tags=["ops"], summary="Readiness probe")
    async def ready() -> JSONResponse:
        # Not ready until the models are resident, or the first real request
        # would pay the load cost and probably time out.
        healthy = detector.is_loaded
        return JSONResponse(
            status_code=200 if healthy else 503,
            content={
                "status": "ready" if healthy else "not_ready",
                "checks": {"face_models": "loaded" if healthy else "not_loaded"},
            },
        )

    return app


app = create_app()
