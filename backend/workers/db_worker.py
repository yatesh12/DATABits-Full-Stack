from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from core.config import get_settings
from core.database import async_session_factory

logger = logging.getLogger(__name__)

settings = get_settings()


class DatabaseWorker:
    def __init__(
        self,
        poll_interval: int = 30,
        job_timeout_minutes: int = 60,
        session_expiry_hours: int = 24,
    ) -> None:
        self._poll_interval = poll_interval
        self._job_timeout_minutes = job_timeout_minutes
        self._session_expiry_hours = session_expiry_hours
        self._running = False

    async def start(self) -> None:
        self._running = True
        logger.info("DatabaseWorker started (poll_interval=%ds)", self._poll_interval)

        while self._running:
            try:
                await self._process_pending_jobs()
                await self._cleanup_expired_sessions()
                await self._update_usage_statistics()
            except Exception as e:
                logger.error("DatabaseWorker error: %s", e)

            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> None:
        self._running = False
        logger.info("DatabaseWorker stopped")

    async def _process_pending_jobs(self) -> None:
        from sqlalchemy import select, update
        from models.jobs import JobModel

        async with async_session_factory() as session:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=self._job_timeout_minutes)

            stmt = (
                select(JobModel)
                .where(JobModel.status.in_(["pending", "running"]))
                .order_by(JobModel.priority.desc(), JobModel.created_at)
                .limit(10)
            )
            result = await session.execute(stmt)
            jobs = list(result.scalars().all())

            for job in jobs:
                if job.status == "running" and job.started_at and job.started_at < cutoff:
                    stmt = (
                        update(JobModel)
                        .where(JobModel.id == job.id)
                        .values(
                            status="failed",
                            error_message="Job timed out",
                        )
                    )
                    await session.execute(stmt)
                    logger.warning("Job %s timed out", job.id)
                elif job.status == "pending":
                    stmt = (
                        update(JobModel)
                        .where(JobModel.id == job.id)
                        .values(
                            status="running",
                            started_at=datetime.now(timezone.utc),
                        )
                    )
                    await session.execute(stmt)
                    logger.info("Job %s started", job.id)

            await session.commit()

    async def _cleanup_expired_sessions(self) -> None:
        from sqlalchemy import delete
        from models.auth import SessionModel

        async with async_session_factory() as session:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=self._session_expiry_hours)

            stmt = delete(SessionModel).where(
                SessionModel.created_at < cutoff,
                SessionModel.is_revoked == False,
            )
            result = await session.execute(stmt)
            if result.rowcount > 0:
                logger.info("Cleaned up %d expired sessions", result.rowcount)
            await session.commit()

    async def _update_usage_statistics(self) -> None:
        from sqlalchemy import select, func
        from models.auth import TenantModel
        from models.data_platform import DatasetModel

        async with async_session_factory() as session:
            tenant_count = await session.execute(
                select(func.count(TenantModel.id))
            )
            dataset_count = await session.execute(
                select(func.count(DatasetModel.id))
            )
            total_storage = await session.execute(
                select(func.coalesce(func.sum(DatasetModel.file_size), 0))
            )

            logger.info(
                "Usage stats - tenants: %d, datasets: %d, storage: %d bytes",
                tenant_count.scalar_one(),
                dataset_count.scalar_one(),
                total_storage.scalar_one(),
            )


async def run_db_worker_forever(
    poll_interval: int = 30,
    job_timeout_minutes: int = 60,
    session_expiry_hours: int = 24,
) -> None:
    worker = DatabaseWorker(
        poll_interval=poll_interval,
        job_timeout_minutes=job_timeout_minutes,
        session_expiry_hours=session_expiry_hours,
    )
    await worker.start()


if __name__ == "__main__":
    asyncio.run(run_db_worker_forever())
