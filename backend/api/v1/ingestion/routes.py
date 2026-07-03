from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_principal
from api.v1.ingestion.schemas import (
    CreateSourceRequest,
    IngestionJobResponse,
    MessageResponse,
    SourceResponse,
    UpdateSourceRequest,
)
from api.v1.ingestion.service import (
    create_source,
    delete_source,
    get_ingestion_job,
    get_source,
    list_ingestion_jobs,
    list_sources,
    trigger_sync,
    update_source,
)
from models.auth import UserModel

router = APIRouter(tags=["ingestion"], prefix="/ingestion")


@router.post("/sources", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source_endpoint(
    body: CreateSourceRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> SourceResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    source = await create_source(session, current_user.tenant_id, body.name, body.source_type, body.config)
    return SourceResponse(
        id=source.id,
        name=source.name,
        source_type=source.source_type,
        config=source.config,
        status=source.status,
        last_sync_at=source.last_sync_at,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@router.get("/sources", response_model=list[SourceResponse])
async def list_sources_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[SourceResponse]:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    sources = await list_sources(session, current_user.tenant_id, limit, offset)
    return [
        SourceResponse(
            id=s.id,
            name=s.name,
            source_type=s.source_type,
            config=s.config,
            status=s.status,
            last_sync_at=s.last_sync_at,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sources
    ]


@router.get("/sources/{source_id}", response_model=SourceResponse)
async def get_source_endpoint(
    source_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> SourceResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    source = await get_source(session, source_id, current_user.tenant_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return SourceResponse(
        id=source.id,
        name=source.name,
        source_type=source.source_type,
        config=source.config,
        status=source.status,
        last_sync_at=source.last_sync_at,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@router.patch("/sources/{source_id}", response_model=SourceResponse)
async def update_source_endpoint(
    source_id: int,
    body: UpdateSourceRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> SourceResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    source = await get_source(session, source_id, current_user.tenant_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    updates = body.model_dump(exclude_unset=True)
    source = await update_source(session, source, updates)
    return SourceResponse(
        id=source.id,
        name=source.name,
        source_type=source.source_type,
        config=source.config,
        status=source.status,
        last_sync_at=source.last_sync_at,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@router.delete("/sources/{source_id}", response_model=MessageResponse)
async def delete_source_endpoint(
    source_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    source = await get_source(session, source_id, current_user.tenant_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    await delete_source(session, source)
    return MessageResponse(message="Source deleted successfully")


@router.post("/sources/{source_id}/sync", response_model=IngestionJobResponse)
async def sync_source(
    source_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> IngestionJobResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    source = await get_source(session, source_id, current_user.tenant_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    job = await trigger_sync(session, source, current_user.id)
    return IngestionJobResponse(
        id=job.id,
        source_type=job.source_type,
        status=job.status,
        progress=job.progress,
        error_message=job.error_message,
        files_processed=job.files_processed,
        rows_ingested=job.rows_ingested,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )


@router.get("/jobs", response_model=list[IngestionJobResponse])
async def list_ingestion_jobs_endpoint(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[IngestionJobResponse]:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    jobs = await list_ingestion_jobs(session, current_user.tenant_id, limit, offset, status)
    return [
        IngestionJobResponse(
            id=j.id,
            source_type=j.source_type,
            status=j.status,
            progress=j.progress,
            error_message=j.error_message,
            files_processed=j.files_processed,
            rows_ingested=j.rows_ingested,
            started_at=j.started_at,
            completed_at=j.completed_at,
            created_at=j.created_at,
        )
        for j in jobs
    ]


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
async def get_ingestion_job_endpoint(
    job_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> IngestionJobResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    job = await get_ingestion_job(session, job_id, current_user.tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return IngestionJobResponse(
        id=job.id,
        source_type=job.source_type,
        status=job.status,
        progress=job.progress,
        error_message=job.error_message,
        files_processed=job.files_processed,
        rows_ingested=job.rows_ingested,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )
