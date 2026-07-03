from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from core.config import get_settings
from core.database import engine
from core.redis_client import check_redis_health

logger = logging.getLogger(__name__)
settings = get_settings()


async def check_db_health() -> dict[str, Any]:
    start = time.perf_counter()
    result: dict[str, Any] = {
        "status": "unknown",
        "latency_ms": 0,
        "error": None,
    }
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        elapsed = (time.perf_counter() - start) * 1000
        result["status"] = "healthy"
        result["latency_ms"] = round(elapsed, 2)
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        result["status"] = "unhealthy"
        result["latency_ms"] = round(elapsed, 2)
        result["error"] = str(e)
        logger.error("Database health check failed: %s", e)
    return result


async def check_redis_health_full() -> dict[str, Any]:
    start = time.perf_counter()
    result: dict[str, Any] = {
        "status": "unknown",
        "latency_ms": 0,
        "error": None,
    }
    try:
        healthy = await check_redis_health()
        elapsed = (time.perf_counter() - start) * 1000
        if healthy:
            result["status"] = "healthy"
        else:
            result["status"] = "unhealthy"
            result["error"] = "Redis ping failed"
        result["latency_ms"] = round(elapsed, 2)
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        result["status"] = "unhealthy"
        result["latency_ms"] = round(elapsed, 2)
        result["error"] = str(e)
        logger.error("Redis health check failed: %s", e)
    return result


async def check_storage_health() -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "unknown",
        "error": None,
        "bucket": settings.S3_BUCKET_NAME,
        "endpoint": settings.S3_ENDPOINT,
    }
    if not settings.S3_ENDPOINT or not settings.S3_ACCESS_KEY_ID:
        result["status"] = "not_configured"
        result["error"] = "S3 storage is not configured"
        return result

    start = time.perf_counter()
    try:
        import boto3
        from botocore.exceptions import ClientError, EndpointConnectionError

        client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
            use_ssl=settings.S3_USE_SSL,
        )
        client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        elapsed = (time.perf_counter() - start) * 1000
        result["status"] = "healthy"
        result["latency_ms"] = round(elapsed, 2)
    except ClientError as e:
        elapsed = (time.perf_counter() - start) * 1000
        result["status"] = "unhealthy"
        result["latency_ms"] = round(elapsed, 2)
        result["error"] = str(e)
    except EndpointConnectionError as e:
        result["status"] = "unreachable"
        result["error"] = str(e)
    except Exception as e:
        result["status"] = "unhealthy"
        result["error"] = str(e)
        logger.error("Storage health check failed: %s", e)
    return result


async def check_all_health() -> dict[str, Any]:
    import asyncio

    db_task = asyncio.create_task(check_db_health())
    redis_task = asyncio.create_task(check_redis_health_full())
    storage_task = asyncio.create_task(check_storage_health())

    db_result, redis_result, storage_result = await asyncio.gather(
        db_task, redis_task, storage_task, return_exceptions=True
    )

    overall_status = "healthy"

    def extract_result(r: Any, name: str) -> dict[str, Any]:
        nonlocal overall_status
        if isinstance(r, Exception):
            overall_status = "degraded"
            return {"status": "error", "error": str(r)}
        if r.get("status") != "healthy":
            overall_status = "degraded"
        return r

    components = {
        "database": extract_result(db_result, "database"),
        "redis": extract_result(redis_result, "redis"),
        "storage": extract_result(storage_result, "storage"),
    }

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "application": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "components": components,
    }


async def get_system_info() -> dict[str, Any]:
    import os
    import platform

    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "hostname": platform.node(),
        "pid": os.getpid(),
        "timezone": time.tzname,
        "uptime_seconds": time.time() - time.monotonic(),
    }
