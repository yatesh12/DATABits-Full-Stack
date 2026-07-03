from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from core.config import get_settings

settings = get_settings()


class HealthStatus(BaseModel):
    status: str
    version: str
    timestamp: str
    database: str
    redis: str
    storage: str


class LivenessStatus(BaseModel):
    status: str = "alive"


class ReadinessStatus(BaseModel):
    status: str
    checks: dict[str, str]


router = APIRouter(tags=["health"], prefix="/health")


@router.get("", response_model=HealthStatus)
async def health_check(
    session: AsyncSession = Depends(get_db),
) -> HealthStatus:
    db_status = "healthy"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    redis_status = "healthy"
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
    except Exception:
        redis_status = "unhealthy"

    storage_status = "healthy"
    # TODO: Check S3/local storage accessibility

    overall = "healthy"
    if db_status != "healthy" or redis_status != "healthy" or storage_status != "healthy":
        overall = "degraded"

    return HealthStatus(
        status=overall,
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        database=db_status,
        redis=redis_status,
        storage=storage_status,
    )


@router.get("/live", response_model=LivenessStatus)
async def liveness() -> LivenessStatus:
    return LivenessStatus()


@router.get("/ready", response_model=ReadinessStatus)
async def readiness(
    session: AsyncSession = Depends(get_db),
) -> ReadinessStatus:
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ready"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ready"
    except Exception as e:
        checks["redis"] = f"unhealthy: {e}"

    all_ready = all(v == "ready" for v in checks.values())
    return ReadinessStatus(
        status="ready" if all_ready else "not_ready",
        checks=checks,
    )
