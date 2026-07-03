from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.billing import PlanModel, SubscriptionModel, TransactionModel, UsageModel, WebhookEventModel
from repositories.base import BaseRepository


class BillingRepository(BaseRepository[PlanModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PlanModel)

    async def get_active_plans(self) -> list[PlanModel]:
        stmt = (
            select(PlanModel)
            .where(PlanModel.is_active == True)
            .order_by(PlanModel.sort_order)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_tenant_subscription(self, tenant_id: uuid.UUID) -> Optional[SubscriptionModel]:
        stmt = (
            select(SubscriptionModel)
            .where(
                and_(
                    SubscriptionModel.tenant_id == tenant_id,
                    SubscriptionModel.status == "active",
                )
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_transaction(self, data: dict[str, Any]) -> TransactionModel:
        instance = TransactionModel(**data)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def get_usage(
        self,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> list[UsageModel]:
        stmt = (
            select(UsageModel)
            .where(
                and_(
                    UsageModel.tenant_id == tenant_id,
                    UsageModel.date >= start_date,
                    UsageModel.date <= end_date,
                )
            )
            .order_by(UsageModel.date)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_webhook_event(self, data: dict[str, Any]) -> WebhookEventModel:
        event_id = data.get("event_id")
        stmt = select(WebhookEventModel).where(WebhookEventModel.event_id == event_id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            await self._session.flush()
            await self._session.refresh(existing)
            return existing

        instance = WebhookEventModel(**data)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance
