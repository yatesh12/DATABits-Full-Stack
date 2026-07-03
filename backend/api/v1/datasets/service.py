from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import get_settings
from models.auth import UserModel
from models.data_platform import DatasetModel, VersionModel
from models.jobs import JobModel
from models.platform import ProjectHistoryModel

settings = get_settings()


async def list_datasets(
    session: AsyncSession,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    status: str | None = None,
) -> tuple[list[DatasetModel], int]:
    query = select(DatasetModel).where(
        DatasetModel.tenant_id == tenant_id,
    )
    count_query = select(func.count(DatasetModel.id)).where(
        DatasetModel.tenant_id == tenant_id,
    )

    if search:
        search_filter = DatasetModel.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    if status:
        query = query.where(DatasetModel.status == status)
        count_query = count_query.where(DatasetModel.status == status)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        query
        .order_by(DatasetModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(query)
    datasets = list(result.scalars().all())
    return datasets, total


async def get_dataset(
    session: AsyncSession,
    dataset_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> DatasetModel | None:
    result = await session.execute(
        select(DatasetModel)
        .options(selectinload(DatasetModel.versions))
        .where(DatasetModel.id == dataset_id, DatasetModel.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def update_dataset(
    session: AsyncSession,
    dataset: DatasetModel,
    updates: dict[str, Any],
) -> DatasetModel:
    for key, value in updates.items():
        setattr(dataset, key, value)
    dataset.updated_at = datetime.now(timezone.utc)
    session.add(dataset)
    await session.flush()
    return dataset


async def delete_dataset(
    session: AsyncSession,
    dataset: DatasetModel,
) -> None:
    await session.delete(dataset)
    await session.flush()


async def create_processing_job(
    session: AsyncSession,
    dataset: DatasetModel,
    user: UserModel,
    config: dict[str, Any] | None,
) -> JobModel:
    job = JobModel(
        tenant_id=dataset.tenant_id,
        user_id=user.id,
        dataset_id=dataset.id,
        type="processing",
        status="pending",
        config=config or {},
    )
    session.add(job)
    await session.flush()
    return job


async def get_dataset_preview(
    session: AsyncSession,
    dataset: DatasetModel,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    row_count = dataset.row_count or 0
    total_pages = max(1, (row_count + page_size - 1) // page_size)
    columns = [c.get("name", f"col_{i}") for i, c in enumerate(dataset.columns_meta or [])]
    return {
        "columns": columns,
        "rows": [],
        "total_rows": row_count,
        "page": page,
        "page_size": page_size,
    }


async def get_dataset_summary(
    session: AsyncSession,
    dataset: DatasetModel,
) -> dict[str, Any]:
    return {
        "row_count": dataset.row_count or 0,
        "column_count": dataset.column_count or 0,
        "file_size": dataset.file_size or 0,
        "columns": dataset.columns_meta or [],
        "missing_cells": 0,
        "total_cells": (dataset.row_count or 0) * (dataset.column_count or 0),
        "missing_percentage": 0.0,
        "duplicate_rows": 0,
        "memory_usage": "0 B",
    }


async def get_dataset_history(
    session: AsyncSession,
    dataset_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[ProjectHistoryModel]:
    result = await session.execute(
        select(ProjectHistoryModel)
        .where(
            ProjectHistoryModel.entity_type == "dataset",
            ProjectHistoryModel.entity_id == str(dataset_id),
        )
        .order_by(ProjectHistoryModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_versions(
    session: AsyncSession,
    dataset_id: uuid.UUID,
) -> list[VersionModel]:
    result = await session.execute(
        select(VersionModel)
        .where(VersionModel.dataset_id == dataset_id)
        .order_by(VersionModel.version_number.desc())
    )
    return list(result.scalars().all())


async def create_version(
    session: AsyncSession,
    dataset: DatasetModel,
    user_id: uuid.UUID | None,
    changes_summary: dict[str, Any] | None = None,
) -> VersionModel:
    version = VersionModel(
        dataset_id=dataset.id,
        version_number=dataset.version + 1,
        file_size=dataset.file_size,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        changes_summary=changes_summary,
        created_by=user_id,
    )
    session.add(version)
    dataset.version = dataset.version + 1
    session.add(dataset)
    await session.flush()
    return version
