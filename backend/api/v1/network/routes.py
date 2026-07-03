from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from api.v1.network.schemas import NetworkStatusResponse, PulseResponse, SignalResponse
from core.config import get_settings

settings = get_settings()

router = APIRouter(tags=["network"], prefix="/network")


@router.get("/signals", response_model=SignalResponse)
async def network_signals(
    session: AsyncSession = Depends(get_db),
) -> SignalResponse:
    start = time.monotonic()
    details: dict[str, bool] = {}

    try:
        await session.execute(text("SELECT 1"))
        details["database"] = True
        has_db = True
    except Exception:
        details["database"] = False
        has_db = False

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        details["redis"] = True
        has_cache = True
    except Exception:
        details["redis"] = False
        has_cache = False

    latency_ms = (time.monotonic() - start) * 1000

    return SignalResponse(
        has_internet=True,
        has_api_access=True,
        has_database_access=has_db,
        has_cache_access=has_cache,
        latency_ms=round(latency_ms, 2),
        details=details,
    )


@router.get("/pulse", response_model=PulseResponse)
async def network_pulse() -> PulseResponse:
    return PulseResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=None,
    )


@router.get("/status", response_model=NetworkStatusResponse)
async def network_status(
    session: AsyncSession = Depends(get_db),
) -> NetworkStatusResponse:
    api_status = "healthy"
    db_status = "healthy"
    cache_status = "healthy"
    storage_status = "healthy"
    external_apis: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
    except Exception:
        cache_status = "unhealthy"

    if settings.GROQ_API_KEY:
        external_apis["groq"] = "configured"
    if settings.STRIPE_API_KEY:
        external_apis["stripe"] = "configured"
    if settings.S3_ENDPOINT:
        external_apis["s3"] = "configured"

    unhealthy = [s for s in [db_status, cache_status, storage_status] if s == "unhealthy"]
    overall = "healthy" if not unhealthy else "degraded"

    return NetworkStatusResponse(
        overall=overall,
        api=api_status,
        database=db_status,
        cache=cache_status,
        storage=storage_status,
        external_apis=external_apis,
    )
