from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=10000)
    conversation_id: str | None = None
    dataset_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    sources: list[dict[str, Any]] | None = None


class QueryRequest(BaseModel):
    query: str = Field(..., max_length=2000)
    dataset_id: str
    max_results: int = Field(10, ge=1, le=100)


class QueryResponse(BaseModel):
    answer: str
    sql_query: str | None = None
    results: list[dict[str, Any]] | None = None
    execution_time_ms: float | None = None


class SuggestRequest(BaseModel):
    dataset_id: str
    goal: str | None = Field(None, max_length=500)
    constraints: list[str] | None = None


class SuggestResponse(BaseModel):
    steps: list[dict[str, Any]]
    explanation: str


class AnalyzeRequest(BaseModel):
    dataset_id: str
    questions: list[str] = Field(..., min_length=1, max_length=10)


class AnalyzeResponse(BaseModel):
    insights: list[dict[str, Any]]
    summary: str


class ConversationResponse(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(None, max_length=255)
    dataset_id: str | None = None


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    metadata: dict[str, Any] | None
    created_at: datetime
