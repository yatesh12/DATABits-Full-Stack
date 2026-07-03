from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DatasetResponse(BaseModel):
    id: str
    name: str
    original_filename: str | None
    file_size: int | None
    mime_type: str | None
    row_count: int | None
    column_count: int | None
    columns_meta: list[dict[str, Any]] | None
    status: str
    storage_backend: str
    version: int
    created_at: datetime
    updated_at: datetime


class DatasetListResponse(BaseModel):
    items: list[DatasetResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DatasetUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=500)


class ProcessingRequest(BaseModel):
    config: dict[str, Any] | None = None


class PreviewResponse(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    total_rows: int
    page: int
    page_size: int


class SummaryResponse(BaseModel):
    row_count: int
    column_count: int
    file_size: int
    columns: list[dict[str, Any]]
    missing_cells: int
    total_cells: int
    missing_percentage: float
    duplicate_rows: int
    memory_usage: str


class MissingValuesRequest(BaseModel):
    strategy: str = Field(..., pattern=r"^(drop|fill_mean|fill_median|fill_mode|fill_constant|interpolate)$")
    columns: list[str] | None = None
    fill_value: Any | None = None


class NormalizeRequest(BaseModel):
    method: str = Field(..., pattern=r"^(minmax|zscore|robust|maxabs)$")
    columns: list[str] | None = None


class EncodeRequest(BaseModel):
    method: str = Field(..., pattern=r"^(label|onehot|ordinal|binary)$")
    columns: list[str] = Field(..., min_length=1)


class OutliersRequest(BaseModel):
    method: str = Field(..., pattern=r"^(zscore|iqr|isolation_forest)$")
    threshold: float = 3.0
    columns: list[str] | None = None


class CorrelationResponse(BaseModel):
    method: str
    matrix: list[list[float]]
    columns: list[str]


class ExportResponse(BaseModel):
    download_url: str


class HistoryResponse(BaseModel):
    id: int
    action: str
    details: dict[str, Any] | None
    created_at: datetime


class VersionResponse(BaseModel):
    id: int
    version_number: int
    file_size: int | None
    row_count: int | None
    column_count: int | None
    changes_summary: dict[str, Any] | None
    created_by: str | None
    created_at: datetime


class VersionCreateRequest(BaseModel):
    changes_summary: dict[str, Any] | None = None


class QualityReportResponse(BaseModel):
    completeness: dict[str, Any]
    uniqueness: dict[str, Any]
    validity: dict[str, Any]
    consistency: dict[str, Any]
    timeliness: dict[str, Any]
    overall_score: float


class MessageResponse(BaseModel):
    message: str
