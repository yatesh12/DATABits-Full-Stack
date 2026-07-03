from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.data_platform import IngestionJobModel, SourceConnectionModel


async def create_source(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
    source_type: str,
    config: dict[str, Any],
) -> SourceConnectionModel:
    source = SourceConnectionModel(
        tenant_id=tenant_id,
        name=name,
        source_type=source_type,
        config=config,
        status="active",
    )
    session.add(source)
    await session.flush()
    return source


async def list_sources(
    session: AsyncSession, tenant_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> list[SourceConnectionModel]:
    result = await session.execute(
        select(SourceConnectionModel)
        .where(SourceConnectionModel.tenant_id == tenant_id)
        .order_by(SourceConnectionModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_source(
    session: AsyncSession, source_id: int, tenant_id: uuid.UUID
) -> SourceConnectionModel | None:
    result = await session.execute(
        select(SourceConnectionModel).where(
            SourceConnectionModel.id == source_id,
            SourceConnectionModel.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def update_source(
    session: AsyncSession,
    source: SourceConnectionModel,
    updates: dict[str, Any],
) -> SourceConnectionModel:
    for key, value in updates.items():
        setattr(source, key, value)
    source.updated_at = datetime.now(timezone.utc)
    session.add(source)
    await session.flush()
    return source


async def delete_source(
    session: AsyncSession, source: SourceConnectionModel
) -> None:
    await session.delete(source)
    await session.flush()


async def trigger_sync(
    session: AsyncSession,
    source: SourceConnectionModel,
    user_id: uuid.UUID,
) -> IngestionJobModel:
    job = IngestionJobModel(
        tenant_id=source.tenant_id,
        user_id=user_id,
        source_type=source.source_type,
        source_config=source.config,
        status="pending",
    )
    session.add(job)
    await session.flush()
    source.last_sync_at = datetime.now(timezone.utc)
    session.add(source)
    await session.flush()
    return job


async def list_ingestion_jobs(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
) -> list[IngestionJobModel]:
    query = select(IngestionJobModel).where(
        IngestionJobModel.tenant_id == tenant_id
    )
    if status:
        query = query.where(IngestionJobModel.status == status)
    query = query.order_by(IngestionJobModel.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_ingestion_job(
    session: AsyncSession, job_id: int, tenant_id: uuid.UUID
) -> IngestionJobModel | None:
    result = await session.execute(
        select(IngestionJobModel).where(
            IngestionJobModel.id == job_id,
            IngestionJobModel.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()
