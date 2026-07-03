from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    tenant_id: str
    user_id: str | None
    event_type: str
    resource_type: str
    resource_id: str | None
    action: str
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditStatsResponse(BaseModel):
    total_events: int
    events_by_type: dict[str, int]
    events_by_action: dict[str, int]
    events_by_resource: dict[str, int]
    timeframe_days: int
