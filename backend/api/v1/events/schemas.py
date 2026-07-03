from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateEventRequest(BaseModel):
    title: str = Field(..., max_length=500)
    description: str | None = None
    event_type: str = Field(..., pattern=r"^(webinar|workshop|conference|meetup|hackathon|other)$")
    starts_at: datetime
    ends_at: datetime | None = None
    location: str | None = Field(None, max_length=500)
    max_attendees: int | None = Field(None, ge=1)
    metadata: dict[str, Any] | None = None


class EventResponse(BaseModel):
    id: int
    title: str
    description: str | None
    event_type: str
    starts_at: datetime
    ends_at: datetime | None
    location: str | None
    max_attendees: int | None
    attendee_count: int = 0
    is_registered: bool = False
    metadata: dict[str, Any] | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime


class RegisterEventResponse(BaseModel):
    registered: bool
    attendee_count: int


class MessageResponse(BaseModel):
    message: str
