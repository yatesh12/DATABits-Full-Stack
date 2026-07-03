from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CommunityRecipeResponse(BaseModel):
    id: str
    name: str
    description: str | None
    steps: list[dict[str, Any]]
    version: int
    like_count: int
    created_by: str | None
    created_at: datetime
    updated_at: datetime


class CommunityDatasetResponse(BaseModel):
    id: str
    name: str
    description: str | None
    row_count: int | None
    column_count: int | None
    file_size: int | None
    tags: list[str]
    download_count: int
    created_by: str | None
    created_at: datetime


class CommunityStatsResponse(BaseModel):
    total_recipes: int
    total_datasets: int
    total_users: int
    total_likes: int
    active_this_week: int


class LikeResponse(BaseModel):
    liked: bool
    like_count: int


class MessageResponse(BaseModel):
    message: str
