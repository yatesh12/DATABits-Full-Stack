from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IntegrationResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    is_connected: bool
    icon_url: str | None = None
    docs_url: str | None = None


class IntegrationConnectRequest(BaseModel):
    credentials: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    scopes: list[str]
    expires_at: datetime | None
    created_at: datetime
    last_used_at: datetime | None


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., max_length=255)
    scopes: list[str] = Field(default_factory=lambda: ["read"])
    expires_at: datetime | None = None


class CreateApiKeyResponse(BaseModel):
    id: int
    name: str
    key: str
    key_prefix: str
    scopes: list[str]
    expires_at: datetime | None
    created_at: datetime


class WebhookResponse(BaseModel):
    id: int
    url: str
    events: list[str]
    is_active: bool
    secret: str | None = None
    created_at: datetime


class CreateWebhookRequest(BaseModel):
    url: str = Field(..., max_length=2048)
    events: list[str] = Field(..., min_length=1)
    secret: str | None = Field(None, min_length=16, max_length=128)


class WebhookTestResponse(BaseModel):
    status_code: int
    body: str
    duration_ms: float


class MessageResponse(BaseModel):
    message: str
