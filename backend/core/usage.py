from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from core.config import get_settings
from core.redis_client import get_redis

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class UsageLimit:
    max_datasets: int
    max_file_size_mb: int
    max_rows: int

    @classmethod
    def default(cls) -> UsageLimit:
        return cls(
            max_datasets=settings.USAGE_MAX_DATASETS_DEFAULT,
            max_file_size_mb=settings.USAGE_MAX_FILE_SIZE_MB,
            max_rows=settings.USAGE_MAX_ROWS_DEFAULT,
        )

    @classmethod
    def unlimited(cls) -> UsageLimit:
        return cls(
            max_datasets=999999,
            max_file_size_mb=999999,
            max_rows=999999999,
        )


PLAN_LIMITS: dict[str, UsageLimit] = {
    "free": UsageLimit(max_datasets=5, max_file_size_mb=10, max_rows=10000),
    "starter": UsageLimit(max_datasets=25, max_file_size_mb=50, max_rows=100000),
    "pro": UsageLimit(max_datasets=100, max_file_size_mb=200, max_rows=1000000),
    "enterprise": UsageLimit.unlimited(),
}


class UsageTracker:
    def __init__(self) -> None:
        self._prefix = "usage"

    def _key(self, tenant_id: str, counter: str) -> str:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"{self._prefix}:{tenant_id}:{counter}:{today}"

    def _limit_key(self, counter: str) -> str:
        return f"{self._prefix}:limit:{counter}"

    async def track_increment(
        self,
        tenant_id: str,
        counter: str,
        amount: int = 1,
    ) -> int:
        redis = await get_redis()
        key = self._key(tenant_id, counter)
        value = await redis.incrby(key, amount)
        await redis.expire(key, 86400 * 2)
        return value

    async def get_usage(
        self,
        tenant_id: str,
        counter: str,
    ) -> int:
        redis = await get_redis()
        key = self._key(tenant_id, counter)
        value = await redis.get(key)
        return int(value) if value else 0

    async def get_all_usage(
        self,
        tenant_id: str,
    ) -> dict[str, int]:
        redis = await get_redis()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        pattern = f"{self._prefix}:{tenant_id}:*:{today}"
        cursor = 0
        usage: dict[str, int] = {}
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                values = await redis.mget(keys)
                for key, val in zip(keys, values):
                    counter_name = key.split(":")[2]
                    usage[counter_name] = int(val) if val else 0
            if cursor == 0:
                break
        return usage

    async def check_limit(
        self,
        tenant_id: str,
        counter: str,
        plan: str = "free",
    ) -> bool:
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
        limit_map: dict[str, int] = {
            "datasets": limits.max_datasets,
            "rows": limits.max_rows,
            "file_size_mb": limits.max_file_size_mb,
        }
        max_allowed = limit_map.get(counter)
        if max_allowed is None:
            return True
        current = await self.get_usage(tenant_id, counter)
        return current < max_allowed

    async def enforce_limit(
        self,
        tenant_id: str,
        counter: str,
        plan: str = "free",
    ) -> None:
        from core.exceptions import PaymentRequiredException

        allowed = await self.check_limit(tenant_id, counter, plan)
        if not allowed:
            limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
            limit_map: dict[str, int] = {
                "datasets": limits.max_datasets,
                "rows": limits.max_rows,
                "file_size_mb": limits.max_file_size_mb,
            }
            raise PaymentRequiredException(
                detail=f"Usage limit exceeded for {counter}. "
                f"Maximum allowed: {limit_map.get(counter, 'N/A')}. "
                f"Please upgrade your plan."
            )

    async def reset_usage(self, tenant_id: str) -> int:
        redis = await get_redis()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        pattern = f"{self._prefix}:{tenant_id}:*:{today}"
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                deleted += await redis.delete(*keys)
            if cursor == 0:
                break
        return deleted


usage_tracker = UsageTracker()
