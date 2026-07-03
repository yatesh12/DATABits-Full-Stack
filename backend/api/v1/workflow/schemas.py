from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StepSchema(BaseModel):
    name: str
    type: str = Field(..., pattern=r"^(clean|transform|encode|normalize|impute|filter|aggregate|custom)$")
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class CreateRecipeRequest(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    steps: list[StepSchema] = Field(..., min_length=1)
    is_template: bool = False


class UpdateRecipeRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    steps: list[StepSchema] | None = None
    is_template: bool | None = None


class RecipeResponse(BaseModel):
    id: str
    name: str
    description: str | None
    steps: list[dict[str, Any]]
    is_template: bool
    is_active: bool
    version: int
    created_by: str | None
    created_at: datetime
    updated_at: datetime


class ExecuteRecipeRequest(BaseModel):
    dataset_id: str


class WorkflowJobResponse(BaseModel):
    id: str
    recipe_id: str
    dataset_id: str | None
    name: str
    status: str
    created_by: str | None
    created_at: datetime
    completed_at: datetime | None


class WorkflowJobDetailResponse(BaseModel):
    id: str
    recipe_id: str
    dataset_id: str | None
    name: str
    status: str
    config_overrides: dict[str, Any] | None
    created_by: str | None
    created_at: datetime
    completed_at: datetime | None
    steps: list[dict[str, Any]]


class MessageResponse(BaseModel):
    message: str
