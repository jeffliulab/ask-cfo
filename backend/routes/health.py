"""Health check endpoint —— /healthz."""

from __future__ import annotations

from fastapi import APIRouter

from backend import __version__

from ._schemas import HealthResponse

router = APIRouter(tags=["meta"])


@router.get("/healthz", response_model=HealthResponse, summary="Liveness probe")
def healthcheck() -> HealthResponse:
    """v0.1 仅做存活检查；v0.4 引入 DB / Redis 后扩成 readiness 探针。"""
    return HealthResponse(status="ok", version=__version__)
