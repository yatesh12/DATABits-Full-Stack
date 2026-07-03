from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.auth import TenantModel, UserModel
from models.billing import UsageModel
from models.data_platform import DatasetModel
from repositories.base import BaseRepository


class TenantRepository(BaseRepository[TenantModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TenantModel)

    async def get_by_slug(self, slug: str) -> Optional[TenantModel]:
        stmt = select(TenantModel).where(TenantModel.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_usage_stats(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        user_count = await self._session.execute(
            select(func.count(UserModel.id)).where(UserModel.tenant_id == tenant_id)
        )
        dataset_count = await self._session.execute(
            select(func.count(DatasetModel.id)).where(DatasetModel.tenant_id == tenant_id)
        )
        total_storage = await self._session.execute(
            select(func.coalesce(func.sum(DatasetModel.file_size), 0)).where(
                DatasetModel.tenant_id == tenant_id
            )
        )
        usage_rows = await self._session.execute(
            select(func.coalesce(func.sum(UsageModel.quantity), 0)).where(
                UsageModel.tenant_id == tenant_id
            )
        )

        return {
            "user_count": user_count.scalar_one(),
            "dataset_count": dataset_count.scalar_one(),
            "total_storage_bytes": total_storage.scalar_one(),
            "total_usage_quantity": usage_rows.scalar_one(),
        }

    async def update_plan(self, tenant_id: uuid.UUID, plan: str) -> Optional[TenantModel]:
        stmt = (
            update(TenantModel)
            .where(TenantModel.id == tenant_id)
            .values(plan=plan)
            .returning(TenantModel)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one_or_none()
