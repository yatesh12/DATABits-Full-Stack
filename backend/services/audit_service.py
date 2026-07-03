from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select, func, and_, between
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session_factory
from models.platform import AuditEventModel


class AuditService:
    async def log_event(
        self,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        event_type: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        action: str = "",
        old_values: Optional[dict[str, Any]] = None,
        new_values: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> dict[str, Any]:
        async with async_session_factory() as session:
            event = AuditEventModel(
                tenant_id=tenant_id,
                user_id=user_id,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                action=action,
                old_values=old_values,
                new_values=new_values,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.add(event)
            await session.flush()
            await session.refresh(event)
            return {
                "id": event.id,
                "tenant_id": str(event.tenant_id),
                "user_id": str(event.user_id) if event.user_id else None,
                "event_type": event.event_type,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "action": event.action,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }

    async def get_logs(
        self,
        tenant_id: uuid.UUID,
        filters: Optional[dict[str, Any]] = None,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        async with async_session_factory() as session:
            stmt = (
                select(AuditEventModel)
                .where(AuditEventModel.tenant_id == tenant_id)
                .order_by(AuditEventModel.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            if filters:
                if "event_type" in filters:
                    stmt = stmt.where(AuditEventModel.event_type == filters["event_type"])
                if "resource_type" in filters:
                    stmt = stmt.where(AuditEventModel.resource_type == filters["resource_type"])
                if "resource_id" in filters:
                    stmt = stmt.where(AuditEventModel.resource_id == filters["resource_id"])
                if "user_id" in filters:
                    stmt = stmt.where(AuditEventModel.user_id == filters["user_id"])
                if "action" in filters:
                    stmt = stmt.where(AuditEventModel.action == filters["action"])
                if "start_date" in filters and "end_date" in filters:
                    stmt = stmt.where(
                        between(
                            AuditEventModel.created_at,
                            filters["start_date"],
                            filters["end_date"],
                        )
                    )

            result = await self._session.execute(stmt)
            events = list(result.scalars().all())
            return [
                {
                    "id": e.id,
                    "tenant_id": str(e.tenant_id),
                    "user_id": str(e.user_id) if e.user_id else None,
                    "event_type": e.event_type,
                    "resource_type": e.resource_type,
                    "resource_id": e.resource_id,
                    "action": e.action,
                    "old_values": e.old_values,
                    "new_values": e.new_values,
                    "ip_address": e.ip_address,
                    "user_agent": e.user_agent,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ]

    async def get_stats(
        self,
        tenant_id: uuid.UUID,
        period: str = "24h",
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        if period == "24h":
            since = now - timedelta(hours=24)
        elif period == "7d":
            since = now - timedelta(days=7)
        elif period == "30d":
            since = now - timedelta(days=30)
        else:
            since = now - timedelta(hours=24)

        async with async_session_factory() as session:
            total_count = await session.execute(
                select(func.count(AuditEventModel.id)).where(
                    and_(
                        AuditEventModel.tenant_id == tenant_id,
                        AuditEventModel.created_at >= since,
                    )
                )
            )

            event_type_counts = await session.execute(
                select(AuditEventModel.event_type, func.count(AuditEventModel.id))
                .where(
                    and_(
                        AuditEventModel.tenant_id == tenant_id,
                        AuditEventModel.created_at >= since,
                    )
                )
                .group_by(AuditEventModel.event_type)
            )

            resource_type_counts = await session.execute(
                select(AuditEventModel.resource_type, func.count(AuditEventModel.id))
                .where(
                    and_(
                        AuditEventModel.tenant_id == tenant_id,
                        AuditEventModel.created_at >= since,
                    )
                )
                .group_by(AuditEventModel.resource_type)
            )

            return {
                "period": period,
                "since": since.isoformat(),
                "total_events": total_count.scalar_one(),
                "by_event_type": dict(event_type_counts.all()),
                "by_resource_type": dict(resource_type_counts.all()),
            }
