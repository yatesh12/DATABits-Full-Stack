from __future__ import annotations

from pydantic import BaseModel


class SignalResponse(BaseModel):
    has_internet: bool
    has_api_access: bool
    has_database_access: bool
    has_cache_access: bool
    latency_ms: float | None = None
    details: dict[str, bool] = {}


class PulseResponse(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float | None = None


class NetworkStatusResponse(BaseModel):
    overall: str
    api: str
    database: str
    cache: str
    storage: str
    external_apis: dict[str, str] = {}
