from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.platform import AuditEventModel


async def list_audit_logs(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    event_type: str | None = None,
    resource_type: str | None = None,
    action: str | None = None,
    user_id: uuid.UUID | None = None,
) -> tuple[list[AuditEventModel], int]:
    query = select(AuditEventModel).where(AuditEventModel.tenant_id == tenant_id)
    count_query = select(func.count(AuditEventModel.id)).where(
        AuditEventModel.tenant_id == tenant_id
    )

    if event_type:
        query = query.where(AuditEventModel.event_type == event_type)
        count_query = count_query.where(AuditEventModel.event_type == event_type)
    if resource_type:
        query = query.where(AuditEventModel.resource_type == resource_type)
        count_query = count_query.where(AuditEventModel.resource_type == resource_type)
    if action:
        query = query.where(AuditEventModel.action == action)
        count_query = count_query.where(AuditEventModel.action == action)
    if user_id:
        query = query.where(AuditEventModel.user_id == user_id)
        count_query = count_query.where(AuditEventModel.user_id == user_id)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        query
        .order_by(AuditEventModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(query)
    return list(result.scalars().all()), total


async def get_audit_log(
    session: AsyncSession, log_id: int, tenant_id: uuid.UUID
) -> AuditEventModel | None:
    result = await session.execute(
        select(AuditEventModel).where(
            AuditEventModel.id == log_id,
            AuditEventModel.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def get_audit_stats(
    session: AsyncSession, tenant_id: uuid.UUID, days: int = 30
) -> dict[str, Any]:
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    base_query = select(AuditEventModel).where(
        AuditEventModel.tenant_id == tenant_id,
        AuditEventModel.created_at >= cutoff,
    )

    total_result = await session.execute(
        select(func.count(AuditEventModel.id)).where(
            AuditEventModel.tenant_id == tenant_id,
            AuditEventModel.created_at >= cutoff,
        )
    )
    total = total_result.scalar() or 0

    type_result = await session.execute(
        select(AuditEventModel.event_type, func.count(AuditEventModel.id))
        .where(
            AuditEventModel.tenant_id == tenant_id,
            AuditEventModel.created_at >= cutoff,
        )
        .group_by(AuditEventModel.event_type)
    )
    events_by_type = dict(type_result.all())

    action_result = await session.execute(
        select(AuditEventModel.action, func.count(AuditEventModel.id))
        .where(
            AuditEventModel.tenant_id == tenant_id,
            AuditEventModel.created_at >= cutoff,
        )
        .group_by(AuditEventModel.action)
    )
    events_by_action = dict(action_result.all())

    resource_result = await session.execute(
        select(AuditEventModel.resource_type, func.count(AuditEventModel.id))
        .where(
            AuditEventModel.tenant_id == tenant_id,
            AuditEventModel.created_at >= cutoff,
        )
        .group_by(AuditEventModel.resource_type)
    )
    events_by_resource = dict(resource_result.all())

    return {
        "total_events": total,
        "events_by_type": events_by_type,
        "events_by_action": events_by_action,
        "events_by_resource": events_by_resource,
        "timeframe_days": days,
    }
