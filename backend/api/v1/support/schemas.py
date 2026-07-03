from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateTicketRequest(BaseModel):
    subject: str = Field(..., max_length=500)
    description: str = Field(..., max_length=10000)
    category: str = Field(..., pattern=r"^(bug|feature|question|billing|account|other)$")
    priority: str = Field("normal", pattern=r"^(low|normal|high|urgent)$")


class TicketResponse(BaseModel):
    id: int
    subject: str
    description: str
    category: str
    priority: str
    status: str
    created_by: str | None
    created_at: datetime
    updated_at: datetime


class TicketReplyRequest(BaseModel):
    message: str = Field(..., max_length=10000)


class TicketReplyResponse(BaseModel):
    id: int
    message: str
    is_staff: bool
    created_by: str | None
    created_at: datetime


class FaqResponse(BaseModel):
    id: int
    question: str
    answer: str
    category: str
    order: int


class DocSearchResponse(BaseModel):
    id: str
    title: str
    excerpt: str
    url: str
    score: float


class MessageResponse(BaseModel):
    message: str
