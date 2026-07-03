from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.jobs import JobModel, JobRunModel


async def list_jobs(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    type: str | None = None,
) -> tuple[list[JobModel], int]:
    query = select(JobModel).where(JobModel.tenant_id == tenant_id)
    count_query = select(func.count(JobModel.id)).where(JobModel.tenant_id == tenant_id)

    if status:
        query = query.where(JobModel.status == status)
        count_query = count_query.where(JobModel.status == status)
    if type:
        query = query.where(JobModel.type == type)
        count_query = count_query.where(JobModel.type == type)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        query
        .order_by(JobModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(query)
    jobs = list(result.scalars().all())
    return jobs, total


async def get_job(
    session: AsyncSession, job_id: uuid.UUID, tenant_id: uuid.UUID
) -> JobModel | None:
    result = await session.execute(
        select(JobModel)
        .options(selectinload(JobModel.runs))
        .where(JobModel.id == job_id, JobModel.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def cancel_job(
    session: AsyncSession, job: JobModel
) -> JobModel:
    job.status = "cancelled"
    session.add(job)
    await session.flush()
    return job


async def delete_job(
    session: AsyncSession, job: JobModel
) -> None:
    await session.delete(job)
    await session.flush()


async def get_job_logs(
    session: AsyncSession, job: JobModel
) -> list[JobRunModel]:
    result = await session.execute(
        select(JobRunModel)
        .where(JobRunModel.job_id == job.id)
        .order_by(JobRunModel.started_at.desc())
    )
    return list(result.scalars().all())
