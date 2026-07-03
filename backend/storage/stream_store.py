from __future__ import annotations

import json
from typing import Any, Optional

from core.config import get_settings

settings = get_settings()


class StreamStore:
    def __init__(self) -> None:
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = await aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
            )
        return self._redis

    async def append_to_stream(
        self,
        stream_id: str,
        data: dict[str, Any],
        maxlen: Optional[int] = 10000,
    ) -> str:
        r = await self._get_redis()
        fields = {k: json.dumps(v) if not isinstance(v, str) else v for k, v in data.items()}
        entry_id = await r.xadd(stream_id, fields, maxlen=maxlen)
        return entry_id

    async def read_stream(
        self,
        stream_id: str,
        offset: str = "0",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        r = await self._get_redis()
        results = await r.xrange(stream_id, min=offset, max="+", count=limit)
        entries = []
        for entry_id, fields in results:
            decoded = {}
            for k, v in fields.items():
                try:
                    decoded[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    decoded[k] = v
            decoded["_id"] = entry_id
            entries.append(decoded)
        return entries

    async def get_stream_metadata(self, stream_id: str) -> dict[str, Any]:
        r = await self._get_redis()
        try:
            info = await r.xinfo_stream(stream_id)
            return {
                "stream_id": stream_id,
                "length": info.get("length", 0),
                "radix_tree_keys": info.get("radix-tree-keys", 0),
                "radix_tree_nodes": info.get("radix-tree-nodes", 0),
                "last_generated_id": info.get("last-generated-id", ""),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
            }
        except Exception:
            return {
                "stream_id": stream_id,
                "length": 0,
                "error": "Stream not found",
            }

    async def delete_stream(self, stream_id: str) -> bool:
        r = await self._get_redis()
        try:
            await r.delete(stream_id)
            return True
        except Exception:
            return False

    async def add_to_group(
        self,
        stream_id: str,
        group_name: str,
        id: str = "$",
    ) -> bool:
        r = await self._get_redis()
        try:
            await r.xgroup_create(stream_id, group_name, id=id, mkstream=True)
            return True
        except Exception:
            return False

    async def read_group(
        self,
        group_name: str,
        consumer_name: str,
        stream_id: str,
        count: int = 10,
        block: int = 1000,
    ) -> list[dict[str, Any]]:
        r = await self._get_redis()
        results = await r.xreadgroup(
            group_name,
            consumer_name,
            {stream_id: ">"},
            count=count,
            block=block,
        )
        entries = []
        for stream_name, messages in results:
            for entry_id, fields in messages:
                decoded = {}
                for k, v in fields.items():
                    try:
                        decoded[k] = json.loads(v)
                    except (json.JSONDecodeError, TypeError):
                        decoded[k] = v
                decoded["_id"] = entry_id
                decoded["_stream"] = stream_name
                entries.append(decoded)
        return entries

    async def ack_message(self, stream_id: str, group_name: str, entry_id: str) -> bool:
        r = await self._get_redis()
        try:
            await r.xack(stream_id, group_name, entry_id)
            return True
        except Exception:
            return False

    async def trim_stream(self, stream_id: str, maxlen: int = 10000) -> int:
        r = await self._get_redis()
        return await r.xtrim(stream_id, maxlen=maxlen)
