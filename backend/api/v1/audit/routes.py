from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_principal
from api.v1.audit.schemas import AuditLogListResponse, AuditLogResponse, AuditStatsResponse
from api.v1.audit.service import get_audit_log, get_audit_stats, list_audit_logs
from models.auth import UserModel

router = APIRouter(tags=["audit"], prefix="/audit")


@router.get("/logs", response_model=AuditLogListResponse)
async def list_audit_logs_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    event_type: str | None = Query(None),
    resource_type: str | None = Query(None),
    action: str | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> AuditLogListResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    logs, total = await list_audit_logs(
        session, current_user.tenant_id, page, page_size,
        event_type, resource_type, action, user_id,
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return AuditLogListResponse(
        items=[
            AuditLogResponse(
                id=log.id,
                tenant_id=str(log.tenant_id),
                user_id=str(log.user_id) if log.user_id else None,
                event_type=log.event_type,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                action=log.action,
                old_values=log.old_values,
                new_values=log.new_values,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log_endpoint(
    log_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> AuditLogResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    log = await get_audit_log(session, log_id, current_user.tenant_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return AuditLogResponse(
        id=log.id,
        tenant_id=str(log.tenant_id),
        user_id=str(log.user_id) if log.user_id else None,
        event_type=log.event_type,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        action=log.action,
        old_values=log.old_values,
        new_values=log.new_values,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        created_at=log.created_at,
    )


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats_endpoint(
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> AuditStatsResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    stats = await get_audit_stats(session, current_user.tenant_id, days)
    return AuditStatsResponse(**stats)
