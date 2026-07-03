from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    upload_id: str
    filename: str
    file_size: int
    mime_type: str
    status: str
    created_at: datetime


class UploadStatusResponse(BaseModel):
    upload_id: str
    filename: str
    status: str
    progress: float | None = None
    error_message: str | None = None
    dataset_id: str | None = None


class UrlUploadRequest(BaseModel):
    url: str = Field(..., max_length=2048)
    filename: str | None = Field(None, max_length=500)


class MultiUploadResponse(BaseModel):
    uploads: list[UploadResponse]
    failed: int = 0


class MessageResponse(BaseModel):
    message: str
