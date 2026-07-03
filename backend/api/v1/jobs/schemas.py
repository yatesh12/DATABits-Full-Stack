from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    dataset_id: str | None
    type: str
    status: str
    progress: float | None
    config: dict[str, Any] | None
    result: dict[str, Any] | None
    error_message: str | None
    priority: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class JobLogResponse(BaseModel):
    id: int
    worker_id: str | None
    logs: list[dict[str, Any]] | None
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    result: dict[str, Any] | None
    error_message: str | None


class MessageResponse(BaseModel):
    message: str
