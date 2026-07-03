from __future__ import annotations

import uuid
from typing import Any, Optional

from celery import Task
from celery.utils.log import get_task_logger
from celery import group

from workers.celery_app import celery_app

logger = get_task_logger(__name__)


class DataTask(Task):
    autoretry_for = (Exception,)
    max_retries = 2
    default_retry_delay = 30


@celery_app.task(bind=True, base=DataTask, name="handle_missing_values_batch")
def handle_missing_values_batch(
    self,
    dataset_ids: list[str],
    strategy: str = "drop",
) -> list[dict[str, Any]]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(
            _execute_missing_values_batch(
                [uuid.UUID(did) for did in dataset_ids],
                strategy,
            )
        )
        return results
    finally:
        loop.close()


async def _execute_missing_values_batch(
    dataset_ids: list[uuid.UUID],
    strategy: str,
) -> list[dict[str, Any]]:
    from services.dataset_service import DatasetService

    service = DatasetService()
    results = []

    for dataset_id in dataset_ids:
        try:
            df = await service.handle_missing_values(dataset_id, strategy=strategy)
            results.append({
                "dataset_id": str(dataset_id),
                "status": "completed",
                "rows": len(df),
            })
        except Exception as e:
            results.append({
                "dataset_id": str(dataset_id),
                "status": "failed",
                "error": str(e),
            })

    return results


@celery_app.task(bind=True, base=DataTask, name="normalize_dataset_batch")
def normalize_dataset_batch(
    self,
    dataset_ids: list[str],
    method: str = "standard",
) -> list[dict[str, Any]]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(
            _execute_normalize_batch(
                [uuid.UUID(did) for did in dataset_ids],
                method,
            )
        )
        return results
    finally:
        loop.close()


async def _execute_normalize_batch(
    dataset_ids: list[uuid.UUID],
    method: str,
) -> list[dict[str, Any]]:
    from services.dataset_service import DatasetService

    service = DatasetService()
    results = []

    for dataset_id in dataset_ids:
        try:
            df = await service.normalize(dataset_id, method=method)
            results.append({
                "dataset_id": str(dataset_id),
                "status": "completed",
                "rows": len(df),
            })
        except Exception as e:
            results.append({
                "dataset_id": str(dataset_id),
                "status": "failed",
                "error": str(e),
            })

    return results


@celery_app.task(bind=True, base=DataTask, name="encode_categorical_batch")
def encode_categorical_batch(
    self,
    dataset_ids: list[str],
    method: str = "label",
) -> list[dict[str, Any]]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(
            _execute_encode_batch(
                [uuid.UUID(did) for did in dataset_ids],
                method,
            )
        )
        return results
    finally:
        loop.close()


async def _execute_encode_batch(
    dataset_ids: list[uuid.UUID],
    method: str,
) -> list[dict[str, Any]]:
    from services.dataset_service import DatasetService

    service = DatasetService()
    results = []

    for dataset_id in dataset_ids:
        try:
            df = await service.encode_categorical(dataset_id, method=method)
            results.append({
                "dataset_id": str(dataset_id),
                "status": "completed",
                "rows": len(df),
            })
        except Exception as e:
            results.append({
                "dataset_id": str(dataset_id),
                "status": "failed",
                "error": str(e),
            })

    return results


@celery_app.task(bind=True, base=DataTask, name="run_quality_check")
def run_quality_check(
    self,
    dataset_id: str,
) -> dict[str, Any]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _execute_quality_check(uuid.UUID(dataset_id))
        )
        return result
    finally:
        loop.close()


async def _execute_quality_check(dataset_id: uuid.UUID) -> dict[str, Any]:
    from services.quality_service import QualityService

    service = QualityService()
    report = await service.run_quality_report(dataset_id)

    from core.database import async_session_factory
    from repositories.dataset_repository import DatasetRepository

    async with async_session_factory() as session:
        repo = DatasetRepository(session)
        await repo.update(dataset_id, {
            "columns_meta": report.get("dtypes", {}),
        })

    return {
        "dataset_id": str(dataset_id),
        "quality_score": report.get("quality_score"),
        "suggestions": report.get("suggestions", []),
    }


@celery_app.task(bind=True, base=DataTask, name="cleanup_temp_files")
def cleanup_temp_files(
    self,
    dataset_id: str,
) -> dict[str, Any]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _execute_temp_cleanup(uuid.UUID(dataset_id))
        )
        return result
    finally:
        loop.close()


async def _execute_temp_cleanup(dataset_id: uuid.UUID) -> dict[str, Any]:
    from pathlib import Path
    from core.config import get_settings

    settings = get_settings()
    temp_dir = Path(settings.FILE_UPLOAD_DIR) / "temp"

    if not temp_dir.exists():
        return {"dataset_id": str(dataset_id), "files_removed": 0}

    count = 0
    for f in temp_dir.glob("*"):
        if f.is_file():
            f.unlink()
            count += 1

    return {
        "dataset_id": str(dataset_id),
        "files_removed": count,
    }
