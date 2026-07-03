from __future__ import annotations

import logging
from typing import Optional

from redis.asyncio import Redis as AsyncRedis
from redis.asyncio.connection import ConnectionPool

from core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

_pool: Optional[ConnectionPool] = None
_redis: Optional[AsyncRedis] = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            url=settings.REDIS_URL,
            max_connections=settings.REDIS_POOL_SIZE,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
            health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
        )
    return _pool


async def get_redis() -> AsyncRedis:
    global _redis
    if _redis is None or not _redis.is_connected():
        pool = _get_pool()
        _redis = AsyncRedis(
            connection_pool=pool,
            decode_responses=True,
        )
        try:
            await _redis.ping()
        except Exception as e:
            logger.error("Redis connection failed: %s", e)
            raise
    return _redis


async def close_redis() -> None:
    global _redis, _pool
    if _redis is not None:
        await _redis.close()
        _redis = None
    if _pool is not None:
        await _pool.disconnect()
        _pool = None


async def check_redis_health() -> bool:
    try:
        redis = await get_redis()
        result = await redis.ping()
        return result is True
    except Exception as e:
        logger.warning("Redis health check failed: %s", e)
        return False


async def get_redis_raw() -> AsyncRedis:
    pool = _get_pool()
    return AsyncRedis(
        connection_pool=pool,
        decode_responses=False,
    )
