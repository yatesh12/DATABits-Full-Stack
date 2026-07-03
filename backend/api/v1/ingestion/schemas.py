from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateSourceRequest(BaseModel):
    name: str = Field(..., max_length=255)
    source_type: str = Field(..., pattern=r"^(s3|gcs|bigquery|mysql|postgresql|mongodb|api|custom)$")
    config: dict[str, Any] = Field(default_factory=dict)


class UpdateSourceRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    config: dict[str, Any] | None = None


class SourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    config: dict[str, Any] | None
    status: str
    last_sync_at: datetime | None
    created_at: datetime
    updated_at: datetime


class IngestionJobResponse(BaseModel):
    id: int
    source_type: str
    status: str
    progress: float | None
    error_message: str | None
    files_processed: int | None
    rows_ingested: int | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class MessageResponse(BaseModel):
    message: str
