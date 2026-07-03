from __future__ import annotations

import json
from typing import Any, Optional, Union

from core.redis_client import get_redis


class CacheService:
    def __init__(self, prefix: str = "cache") -> None:
        self._prefix = prefix

    def _make_key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    async def get(self, key: str, default: Any = None) -> Any:
        redis = await get_redis()
        raw = await redis.get(self._make_key(key))
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        redis = await get_redis()
        serialized = json.dumps(value, default=str)
        cache_key = self._make_key(key)
        if ttl is not None:
            return await redis.setex(cache_key, ttl, serialized)
        return await redis.set(cache_key, serialized)

    async def delete(self, key: str) -> bool:
        redis = await get_redis()
        return bool(await redis.delete(self._make_key(key)))

    async def clear(self, pattern: Optional[str] = None) -> int:
        redis = await get_redis()
        if pattern:
            search_pattern = self._make_key(pattern)
        else:
            search_pattern = f"{self._prefix}:*"

        cursor = 0
        deleted_count = 0
        while True:
            cursor, keys = await redis.scan(
                cursor=cursor,
                match=search_pattern,
                count=100,
            )
            if keys:
                deleted_count += await redis.delete(*keys)
            if cursor == 0:
                break
        return deleted_count

    async def exists(self, key: str) -> bool:
        redis = await get_redis()
        return bool(await redis.exists(self._make_key(key)))

    async def ttl(self, key: str) -> int:
        redis = await get_redis()
        return await redis.ttl(self._make_key(key))

    async def get_or_set(
        self,
        key: str,
        factory: Any,
        ttl: Optional[int] = None,
    ) -> Any:
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = factory() if callable(factory) else factory
        await self.set(key, value, ttl=ttl)
        return value

    async def increment(self, key: str, amount: int = 1) -> int:
        redis = await get_redis()
        return await redis.incrby(self._make_key(key), amount)

    async def set_hash(
        self,
        key: str,
        mapping: dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        redis = await get_redis()
        cache_key = self._make_key(key)
        await redis.hset(cache_key, mapping=mapping)
        if ttl is not None:
            await redis.expire(cache_key, ttl)

    async def get_hash(self, key: str, field: Optional[str] = None) -> Any:
        redis = await get_redis()
        cache_key = self._make_key(key)
        if field:
            return await redis.hget(cache_key, field)
        return await redis.hgetall(cache_key)


cache_service = CacheService()
