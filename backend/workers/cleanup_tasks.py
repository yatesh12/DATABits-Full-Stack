from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from celery import Task
from celery.utils.log import get_task_logger
from celery.schedules import crontab

from workers.celery_app import celery_app

logger = get_task_logger(__name__)


class CleanupTask(Task):
    autoretry_for = (Exception,)
    max_retries = 1
    default_retry_delay = 60


@celery_app.task(bind=True, base=CleanupTask, name="cleanup_expired_datasets")
def cleanup_expired_datasets(self) -> dict[str, Any]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_execute_cleanup_expired_datasets())
        return result
    finally:
        loop.close()


async def _execute_cleanup_expired_datasets() -> dict[str, Any]:
    from sqlalchemy import select, delete
    from core.database import async_session_factory
    from models.data_platform import DatasetModel, VersionModel
    from storage.dataset_store import LocalDatasetStore

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    store = LocalDatasetStore()
    deleted_count = 0

    async with async_session_factory() as session:
        stmt = (
            select(DatasetModel)
            .where(DatasetModel.status == "deleted")
            .where(DatasetModel.updated_at < cutoff)
        )
        result = await session.execute(stmt)
        datasets = list(result.scalars().all())

        for dataset in datasets:
            await store.delete(dataset.id)
            await session.delete(dataset)
            deleted_count += 1

        await session.commit()

    logger.info("Cleanup expired datasets: %d removed", deleted_count)
    return {"datasets_removed": deleted_count}


@celery_app.task(bind=True, base=CleanupTask, name="cleanup_old_versions")
def cleanup_old_versions(
    self,
    dataset_id: str,
    keep_count: int = 5,
) -> dict[str, Any]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _execute_cleanup_old_versions(uuid.UUID(dataset_id), keep_count)
        )
        return result
    finally:
        loop.close()


async def _execute_cleanup_old_versions(
    dataset_id: uuid.UUID,
    keep_count: int,
) -> dict[str, Any]:
    from sqlalchemy import select, delete
    from core.database import async_session_factory
    from models.data_platform import VersionModel

    removed = 0

    async with async_session_factory() as session:
        stmt = (
            select(VersionModel)
            .where(VersionModel.dataset_id == dataset_id)
            .order_by(VersionModel.version_number.desc())
        )
        result = await session.execute(stmt)
        versions = list(result.scalars().all())

        if len(versions) > keep_count:
            to_remove = versions[keep_count:]
            for version in to_remove:
                await session.delete(version)
                removed += 1

        await session.commit()

    logger.info("Cleanup old versions for %s: %d removed", dataset_id, removed)
    return {"dataset_id": dataset_id, "versions_removed": removed}


@celery_app.task(bind=True, base=CleanupTask, name="cleanup_stale_sessions")
def cleanup_stale_sessions(self) -> dict[str, Any]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_execute_cleanup_stale_sessions())
        return result
    finally:
        loop.close()


async def _execute_cleanup_stale_sessions() -> dict[str, Any]:
    from sqlalchemy import delete
    from core.database import async_session_factory
    from models.auth import SessionModel

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    removed = 0

    async with async_session_factory() as session:
        stmt = delete(SessionModel).where(
            SessionModel.expires_at < cutoff,
            SessionModel.is_revoked == False,
        )
        result = await session.execute(stmt)
        removed = result.rowcount
        await session.commit()

    logger.info("Cleanup stale sessions: %d removed", removed)
    return {"sessions_removed": removed}


@celery_app.task(bind=True, base=CleanupTask, name="cleanup_temp_uploads")
def cleanup_temp_uploads(self) -> dict[str, Any]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_execute_cleanup_temp_uploads())
        return result
    finally:
        loop.close()


async def _execute_cleanup_temp_uploads() -> dict[str, Any]:
    from pathlib import Path
    from core.config import get_settings

    settings = get_settings()
    temp_dir = Path(settings.FILE_UPLOAD_DIR) / "uploads"
    removed = 0

    if not temp_dir.exists():
        return {"files_removed": 0}

    cutoff = datetime.now().timestamp() - 86400

    for item in temp_dir.iterdir():
        if item.is_dir():
            item_time = item.stat().st_mtime
            if item_time < cutoff:
                import shutil
                shutil.rmtree(item)
                removed += 1
        elif item.is_file():
            item_time = item.stat().st_mtime
            if item_time < cutoff:
                item.unlink()
                removed += 1

    logger.info("Cleanup temp uploads: %d removed", removed)
    return {"files_removed": removed}


@celery_app.task(bind=True, base=CleanupTask, name="archive_audit_logs")
def archive_audit_logs(
    self,
    older_than_days: int = 90,
) -> dict[str, Any]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _execute_archive_audit_logs(older_than_days)
        )
        return result
    finally:
        loop.close()


async def _execute_archive_audit_logs(older_than_days: int) -> dict[str, Any]:
    from sqlalchemy import select, delete
    from core.database import async_session_factory
    from models.platform import AuditEventModel
    from datetime import timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    archived = 0

    async with async_session_factory() as session:
        stmt = (
            select(AuditEventModel)
            .where(AuditEventModel.created_at < cutoff)
            .limit(1000)
        )
        result = await session.execute(stmt)
        events = list(result.scalars().all())

        import json
        from pathlib import Path
        from core.config import get_settings

        settings = get_settings()
        archive_dir = Path(settings.FILE_UPLOAD_DIR) / "audit_archive"
        archive_dir.mkdir(parents=True, exist_ok=True)

        archive_file = archive_dir / f"audit_{cutoff.strftime('%Y%m%d')}.jsonl"

        with open(archive_file, "a") as f:
            for event in events:
                record = {
                    "id": event.id,
                    "tenant_id": str(event.tenant_id),
                    "user_id": str(event.user_id) if event.user_id else None,
                    "event_type": event.event_type,
                    "resource_type": event.resource_type,
                    "resource_id": event.resource_id,
                    "action": event.action,
                    "old_values": event.old_values,
                    "new_values": event.new_values,
                    "ip_address": event.ip_address,
                    "user_agent": event.user_agent,
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                }
                f.write(json.dumps(record) + "\n")
                await session.delete(event)
                archived += 1

        await session.commit()

    logger.info("Archive audit logs: %d events archived", archived)
    return {
        "events_archived": archived,
        "older_than_days": older_than_days,
    }


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(hour=3, minute=0),
        cleanup_expired_datasets.s(),
        name="cleanup-expired-datasets-daily",
    )
    sender.add_periodic_task(
        crontab(hour=4, minute=0),
        cleanup_stale_sessions.s(),
        name="cleanup-stale-sessions-daily",
    )
    sender.add_periodic_task(
        crontab(hour=5, minute=0),
        cleanup_temp_uploads.s(),
        name="cleanup-temp-uploads-daily",
    )
    sender.add_periodic_task(
        crontab(hour=6, minute=0, day_of_week=0),
        archive_audit_logs.s(older_than_days=90),
        name="archive-audit-logs-weekly",
    )
