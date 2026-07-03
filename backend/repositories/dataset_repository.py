from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.data_platform import DatasetModel, VersionModel, IngestionJobModel
from repositories.base import BaseRepository


class DatasetRepository(BaseRepository[DatasetModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, DatasetModel)

    async def get_by_tenant(
        self,
        tenant_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> list[DatasetModel]:
        stmt = (
            select(DatasetModel)
            .where(DatasetModel.tenant_id == tenant_id)
            .order_by(DatasetModel.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if status:
            stmt = stmt.where(DatasetModel.status == status)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DatasetModel]:
        stmt = (
            select(DatasetModel)
            .where(DatasetModel.user_id == user_id)
            .order_by(DatasetModel.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_versions(self, dataset_id: uuid.UUID) -> list[VersionModel]:
        stmt = (
            select(VersionModel)
            .where(VersionModel.dataset_id == dataset_id)
            .order_by(VersionModel.version_number.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_version(self, dataset_id: uuid.UUID, data: dict[str, Any]) -> VersionModel:
        instance = VersionModel(dataset_id=dataset_id, **data)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def update_status(self, dataset_id: uuid.UUID, status: str) -> Optional[DatasetModel]:
        stmt = (
            update(DatasetModel)
            .where(DatasetModel.id == dataset_id)
            .values(status=status)
            .returning(DatasetModel)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one_or_none()

    async def get_processing_history(self, dataset_id: uuid.UUID) -> list[IngestionJobModel]:
        stmt = (
            select(IngestionJobModel)
            .where(IngestionJobModel.dataset_id == dataset_id)
            .order_by(IngestionJobModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
