from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_principal
from api.v1.jobs.schemas import (
    JobListResponse,
    JobLogResponse,
    JobResponse,
    MessageResponse,
)
from api.v1.jobs.service import (
    cancel_job,
    delete_job,
    get_job,
    get_job_logs,
    list_jobs,
)
from models.auth import UserModel

router = APIRouter(tags=["jobs"], prefix="/jobs")


def _job_to_response(job: object) -> JobResponse:
    return JobResponse(
        id=str(job.id),
        tenant_id=str(job.tenant_id),
        user_id=str(job.user_id),
        dataset_id=str(job.dataset_id) if job.dataset_id else None,
        type=job.type,
        status=job.status,
        progress=job.progress,
        config=job.config,
        result=job.result,
        error_message=job.error_message,
        priority=job.priority,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("", response_model=JobListResponse)
async def list_jobs_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    type: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> JobListResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    jobs, total = await list_jobs(session, current_user.tenant_id, page, page_size, status, type)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return JobListResponse(
        items=[_job_to_response(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_endpoint(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> JobResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    job = await get_job(session, job_id, current_user.tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job_endpoint(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> JobResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    job = await get_job(session, job_id, current_user.tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail="Job cannot be cancelled in its current state")
    job = await cancel_job(session, job)
    return _job_to_response(job)


@router.delete("/{job_id}", response_model=MessageResponse)
async def delete_job_endpoint(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    job = await get_job(session, job_id, current_user.tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail="Only completed, failed, or cancelled jobs can be deleted")
    await delete_job(session, job)
    return MessageResponse(message="Job deleted successfully")


@router.get("/{job_id}/stream")
async def stream_job_progress(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> StreamingResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    job = await get_job(session, job_id, current_user.tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        import asyncio
        job_obj = job
        while job_obj.status in ("pending", "running"):
            yield f"data: {json.dumps({'status': job_obj.status, 'progress': job_obj.progress})}\n\n"
            await asyncio.sleep(2)
            job_obj = await get_job(session, job_id, current_user.tenant_id)
            if job_obj is None:
                break
        yield f"data: {json.dumps({'status': job_obj.status, 'progress': job_obj.progress})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/logs", response_model=list[JobLogResponse])
async def get_job_logs_endpoint(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[JobLogResponse]:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    job = await get_job(session, job_id, current_user.tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    logs = await get_job_logs(session, job)
    return [
        JobLogResponse(
            id=run.id,
            worker_id=run.worker_id,
            logs=run.logs,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            result=run.result,
            error_message=run.error_message,
        )
        for run in logs
    ]
