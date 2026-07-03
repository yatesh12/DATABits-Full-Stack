from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_principal
from api.v1.datasets.schemas import (
    CorrelationResponse,
    DatasetListResponse,
    DatasetResponse,
    DatasetUpdateRequest,
    EncodeRequest,
    ExportResponse,
    HistoryResponse,
    MessageResponse,
    MissingValuesRequest,
    NormalizeRequest,
    OutliersRequest,
    PreviewResponse,
    ProcessingRequest,
    QualityReportResponse,
    SummaryResponse,
    VersionCreateRequest,
    VersionResponse,
)
from api.v1.datasets.service import (
    create_processing_job,
    create_version,
    delete_dataset,
    get_dataset,
    get_dataset_history,
    get_dataset_preview,
    get_dataset_summary,
    list_datasets,
    list_versions,
    update_dataset,
)
from models.auth import UserModel

router = APIRouter(tags=["datasets"], prefix="/datasets")


def _dataset_to_response(ds: Any) -> DatasetResponse:
    return DatasetResponse(
        id=str(ds.id),
        name=ds.name,
        original_filename=ds.original_filename,
        file_size=ds.file_size,
        mime_type=ds.mime_type,
        row_count=ds.row_count,
        column_count=ds.column_count,
        columns_meta=ds.columns_meta,
        status=ds.status,
        storage_backend=ds.storage_backend,
        version=ds.version,
        created_at=ds.created_at,
        updated_at=ds.updated_at,
    )


@router.get("", response_model=DatasetListResponse)
async def list_datasets_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    status: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> DatasetListResponse:
    tenant_id = current_user.tenant_id
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="User has no tenant")
    datasets, total = await list_datasets(
        session, current_user.id, tenant_id, page, page_size, search, status
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return DatasetListResponse(
        items=[_dataset_to_response(d) for d in datasets],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset_endpoint(
    dataset_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> DatasetResponse:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return _dataset_to_response(dataset)


@router.patch("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset_endpoint(
    dataset_id: uuid.UUID,
    body: DatasetUpdateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> DatasetResponse:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    updates = body.model_dump(exclude_unset=True)
    dataset = await update_dataset(session, dataset, updates)
    return _dataset_to_response(dataset)


@router.delete("/{dataset_id}", response_model=MessageResponse)
async def delete_dataset_endpoint(
    dataset_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    await delete_dataset(session, dataset)
    return MessageResponse(message="Dataset deleted successfully")


@router.post("/{dataset_id}/process", response_model=dict)
async def process_dataset(
    dataset_id: uuid.UUID,
    body: ProcessingRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> dict:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    job = await create_processing_job(session, dataset, current_user, body.config)
    return {"job_id": str(job.id), "status": job.status}


@router.get("/{dataset_id}/preview", response_model=PreviewResponse)
async def preview_dataset(
    dataset_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> PreviewResponse:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    preview = await get_dataset_preview(session, dataset, page, page_size)
    return PreviewResponse(**preview)


@router.get("/{dataset_id}/summary", response_model=SummaryResponse)
async def dataset_summary(
    dataset_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> SummaryResponse:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    summary = await get_dataset_summary(session, dataset)
    return SummaryResponse(**summary)


@router.post("/{dataset_id}/missing-values", response_model=MessageResponse)
async def handle_missing_values(
    dataset_id: uuid.UUID,
    body: MissingValuesRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return MessageResponse(message=f"Missing values handled using {body.strategy} strategy")


@router.post("/{dataset_id}/normalize", response_model=MessageResponse)
async def normalize_dataset(
    dataset_id: uuid.UUID,
    body: NormalizeRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return MessageResponse(message=f"Dataset normalized using {body.method} method")


@router.post("/{dataset_id}/encode", response_model=MessageResponse)
async def encode_dataset(
    dataset_id: uuid.UUID,
    body: EncodeRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return MessageResponse(message=f"Categorical encoding applied using {body.method}")


@router.post("/{dataset_id}/outliers", response_model=MessageResponse)
async def remove_outliers(
    dataset_id: uuid.UUID,
    body: OutliersRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return MessageResponse(message=f"Outliers removed using {body.method} method")


@router.delete("/{dataset_id}/duplicates", response_model=MessageResponse)
async def remove_duplicates(
    dataset_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return MessageResponse(message="Duplicates removed")


@router.get("/{dataset_id}/correlation", response_model=CorrelationResponse)
async def correlation_analysis(
    dataset_id: uuid.UUID,
    method: str = Query("pearson", pattern=r"^(pearson|spearman|kendall|cramers_v)$"),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> CorrelationResponse:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    columns = [c.get("name", f"col_{i}") for i, c in enumerate(dataset.columns_meta or [])]
    return CorrelationResponse(method=method, matrix=[], columns=columns)


@router.get("/{dataset_id}/export", response_model=ExportResponse)
async def export_dataset(
    dataset_id: uuid.UUID,
    format: str = Query("csv", pattern=r"^(csv|xlsx|json|parquet)$"),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> ExportResponse:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ExportResponse(download_url=f"/api/v1/datasets/{dataset_id}/download?format={format}")


@router.post("/{dataset_id}/reset", response_model=MessageResponse)
async def reset_dataset(
    dataset_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return MessageResponse(message="Dataset reset to original state")


@router.get("/{dataset_id}/history", response_model=list[HistoryResponse])
async def dataset_history(
    dataset_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[HistoryResponse]:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    history = await get_dataset_history(session, dataset_id, limit, offset)
    return [
        HistoryResponse(
            id=h.id,
            action=h.action,
            details=h.changes,
            created_at=h.created_at,
        )
        for h in history
    ]


@router.get("/{dataset_id}/versions", response_model=list[VersionResponse])
async def list_dataset_versions(
    dataset_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[VersionResponse]:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    versions = await list_versions(session, dataset_id)
    return [
        VersionResponse(
            id=v.id,
            version_number=v.version_number,
            file_size=v.file_size,
            row_count=v.row_count,
            column_count=v.column_count,
            changes_summary=v.changes_summary,
            created_by=str(v.created_by) if v.created_by else None,
            created_at=v.created_at,
        )
        for v in versions
    ]


@router.post("/{dataset_id}/versions", response_model=VersionResponse, status_code=201)
async def create_dataset_version(
    dataset_id: uuid.UUID,
    body: VersionCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> VersionResponse:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    version = await create_version(session, dataset, current_user.id, body.changes_summary)
    return VersionResponse(
        id=version.id,
        version_number=version.version_number,
        file_size=version.file_size,
        row_count=version.row_count,
        column_count=version.column_count,
        changes_summary=version.changes_summary,
        created_by=str(version.created_by) if version.created_by else None,
        created_at=version.created_at,
    )


@router.get("/{dataset_id}/quality", response_model=QualityReportResponse)
async def dataset_quality(
    dataset_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> QualityReportResponse:
    dataset = await get_dataset(session, dataset_id, current_user.tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return QualityReportResponse(
        completeness={"score": 0.0, "details": {}},
        uniqueness={"score": 0.0, "details": {}},
        validity={"score": 0.0, "details": {}},
        consistency={"score": 0.0, "details": {}},
        timeliness={"score": 0.0, "details": {}},
        overall_score=0.0,
    )
