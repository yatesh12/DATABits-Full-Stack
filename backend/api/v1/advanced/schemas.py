from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    dataset_id: str
    model_type: str = Field(..., pattern=r"^(classification|regression|clustering|anomaly)$")
    target_column: str
    test_size: float = Field(0.2, ge=0.1, le=0.5)
    features: list[str] | None = None
    hyperparameters: dict[str, Any] | None = None


class EvaluateResponse(BaseModel):
    model_type: str
    metrics: dict[str, Any]
    feature_importance: dict[str, float] | None = None
    confusion_matrix: list[list[int]] | None = None
    roc_auc: float | None = None
    execution_time_ms: float | None = None


class CatalogItemResponse(BaseModel):
    id: str
    name: str
    type: str
    schema: dict[str, Any]
    row_count: int | None
    size_bytes: int | None
    tags: list[str]
    created_at: str
    updated_at: str


class SampleRequest(BaseModel):
    dataset_id: str
    method: str = Field(..., pattern=r"^(random|stratified|systematic|cluster)$")
    size: int = Field(1000, ge=1, le=1_000_000)
    seed: int | None = None
    strata_column: str | None = None


class SampleResponse(BaseModel):
    sample_size: int
    original_size: int
    method: str
    columns: list[str]
    rows: list[list[Any]]
    execution_time_ms: float | None = None


class ValidateRequest(BaseModel):
    dataset_id: str
    rules: list[dict[str, Any]] = Field(..., min_length=1)
    strict: bool = False


class ValidateResponse(BaseModel):
    passed: bool
    total_rules: int
    passed_rules: int
    failed_rules: int
    results: list[dict[str, Any]]
    execution_time_ms: float | None = None


class TransformRequest(BaseModel):
    dataset_id: str
    operations: list[dict[str, Any]] = Field(..., min_length=1)
    create_version: bool = True


class TransformResponse(BaseModel):
    dataset_id: str
    operations_applied: int
    rows_affected: int | None
    new_version: int | None
    execution_time_ms: float | None = None


class AnalyzeRequest(BaseModel):
    dataset_id: str
    analysis_type: str = Field(..., pattern=r"^(distribution|correlation|clustering|pca|timeseries|anomaly)$")
    config: dict[str, Any] = Field(default_factory=dict)


class AnalyzeResponse(BaseModel):
    analysis_type: str
    results: dict[str, Any]
    charts: dict[str, Any] | None = None
    execution_time_ms: float | None = None
