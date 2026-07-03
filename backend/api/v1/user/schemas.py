from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class ProfileResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: str | None
    avatar_url: str | None
    is_verified: bool
    created_at: datetime | None
    updated_at: datetime | None
    last_login: datetime | None


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(None, max_length=255)
    avatar_url: str | None = Field(None, max_length=2048)


class SettingResponse(BaseModel):
    key: str
    value: dict[str, Any] | None
    updated_at: datetime


class SettingsUpdateRequest(BaseModel):
    settings: dict[str, Any]


class ActivityResponse(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any] | None
    created_at: datetime


class MessageResponse(BaseModel):
    message: str
