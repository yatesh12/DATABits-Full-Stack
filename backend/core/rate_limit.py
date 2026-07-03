from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from fastapi import Depends, HTTPException, Request, status

from core.redis_client import get_redis


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_at: float
    retry_after: Optional[float] = None


class RateLimiter:
    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._redis_url = redis_url

    async def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> RateLimitResult:
        redis = await get_redis()
        now = time.time()
        window_start = now - window_seconds

        pipeline = redis.pipeline()
        pipeline.zadd(key, {str(now): now})
        pipeline.zremrangebyscore(key, 0, window_start)
        pipeline.zcard(key)
        pipeline.expire(key, window_seconds)
        results = await pipeline.execute()

        current_count = results[2]
        allowed = current_count <= max_requests

        oldest_allowed = now
        if current_count > 0:
            scores = await redis.zrange(key, 0, 0, withscores=True)
            if scores:
                oldest_allowed = scores[0][1]

        reset_at = oldest_allowed + window_seconds
        remaining = max(0, max_requests - current_count)
        retry_after = max(0.0, reset_at - now) if not allowed else None

        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=retry_after,
        )


_limiter = RateLimiter()


def rate_limit(
    limit: Optional[int] = None,
    window: Optional[int] = None,
    key_builder: Optional[Callable[[Request], str]] = None,
) -> Callable[[Request], Awaitable[None]]:
    async def _rate_limit_dependency(request: Request) -> None:
        from core.config import get_settings

        settings = get_settings()
        max_req = limit if limit is not None else settings.RATE_LIMIT_MAX_REQUESTS
        win = window if window is not None else settings.RATE_LIMIT_WINDOW_SECONDS

        if key_builder:
            rate_key = key_builder(request)
        else:
            client_ip = request.client.host if request.client else "unknown"
            route_path = request.url.path
            rate_key = f"ratelimit:{client_ip}:{route_path}"

        result = await _limiter.check(rate_key, max_req, win)

        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": result.retry_after,
                    "reset_at": datetime.fromtimestamp(
                        result.reset_at, tz=timezone.utc
                    ).isoformat(),
                },
                headers={
                    "X-RateLimit-Limit": str(max_req),
                    "X-RateLimit-Remaining": str(result.remaining),
                    "X-RateLimit-Reset": str(int(result.reset_at)),
                    "Retry-After": str(int(result.retry_after or 0)),
                },
            )

    return _rate_limit_dependency
