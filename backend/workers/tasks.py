from __future__ import annotations

import uuid
from typing import Any, Optional

from celery import Task
from celery.utils.log import get_task_logger

from workers.celery_app import celery_app

logger = get_task_logger(__name__)


class DatabaseTask(Task):
    _session = None

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if self._session is not None:
            self._session = None


@celery_app.task(bind=True, base=DatabaseTask, name="process_dataset")
def process_dataset_task(
    self,
    dataset_id: str,
    operation: str,
    params: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _execute_dataset_operation(
                uuid.UUID(dataset_id),
                operation,
                params or {},
            )
        )
        return result
    finally:
        loop.close()


async def _execute_dataset_operation(
    dataset_id: uuid.UUID,
    operation: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    from services.dataset_service import DatasetService

    service = DatasetService()

    if operation == "missing_values":
        df = await service.handle_missing_values(
            dataset_id,
            strategy=params.get("strategy", "drop"),
            columns=params.get("columns"),
            fill_value=params.get("fill_value"),
        )
        return {"dataset_id": str(dataset_id), "operation": operation, "rows": len(df), "columns": len(df.columns)}

    elif operation == "normalize":
        df = await service.normalize(
            dataset_id,
            method=params.get("method", "standard"),
            columns=params.get("columns"),
        )
        return {"dataset_id": str(dataset_id), "operation": operation, "rows": len(df), "columns": len(df.columns)}

    elif operation == "encode":
        df = await service.encode_categorical(
            dataset_id,
            method=params.get("method", "label"),
            columns=params.get("columns"),
        )
        return {"dataset_id": str(dataset_id), "operation": operation, "rows": len(df), "columns": len(df.columns)}

    elif operation == "detect_outliers":
        result = await service.detect_outliers(
            dataset_id,
            method=params.get("method", "zscore"),
            threshold=params.get("threshold", 3.0),
            columns=params.get("columns"),
        )
        return {"dataset_id": str(dataset_id), "operation": operation, **result}

    elif operation == "find_duplicates":
        result = await service.find_duplicates(
            dataset_id,
            columns=params.get("columns"),
            keep=params.get("keep", "first"),
        )
        return {"dataset_id": str(dataset_id), "operation": operation, **result}

    elif operation == "correlation":
        result = await service.compute_correlation(
            dataset_id,
            method=params.get("method", "pearson"),
            columns=params.get("columns"),
        )
        return {"dataset_id": str(dataset_id), "operation": operation, **result}

    elif operation == "quality_report":
        from services.quality_service import QualityService

        qs = QualityService()
        report = await qs.run_quality_report(dataset_id)
        return {"dataset_id": str(dataset_id), "operation": operation, "report": report}

    else:
        raise ValueError(f"Unknown operation: {operation}")


@celery_app.task(bind=True, base=DatabaseTask, name="run_workflow_job")
def run_workflow_job(
    self,
    workflow_job_id: str,
) -> dict[str, Any]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _execute_workflow_job(uuid.UUID(workflow_job_id))
        )
        return result
    finally:
        loop.close()


async def _execute_workflow_job(workflow_job_id: uuid.UUID) -> dict[str, Any]:
    from core.database import async_session_factory
    from models.workflow import WorkflowJobModel, WorkflowJobLogModel
    from sqlalchemy import select, update
    from datetime import datetime, timezone

    async with async_session_factory() as session:
        stmt = select(WorkflowJobModel).where(WorkflowJobModel.id == workflow_job_id)
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()

        if job is None:
            raise ValueError(f"Workflow job {workflow_job_id} not found")

        stmt = (
            update(WorkflowJobModel)
            .where(WorkflowJobModel.id == workflow_job_id)
            .values(status="running")
        )
        await session.execute(stmt)
        await session.flush()

        recipe = job.recipe
        if recipe is None:
            await session.execute(
                update(WorkflowJobModel)
                .where(WorkflowJobModel.id == workflow_job_id)
                .values(status="failed")
            )
            await session.commit()
            raise ValueError(f"Recipe not found for job {workflow_job_id}")

        steps = recipe.steps
        overall_status = "completed"
        step_results = []

        for idx, step in enumerate(steps):
            log_entry = WorkflowJobLogModel(
                workflow_job_id=workflow_job_id,
                step_index=idx,
                step_name=step.get("name", f"step_{idx}"),
                status="running",
                input=step,
                started_at=datetime.now(timezone.utc),
            )
            session.add(log_entry)
            await session.flush()

            try:
                step_type = step.get("type", "")
                step_params = step.get("params", {})
                dataset_id_str = step_params.get("dataset_id") or str(job.dataset_id) if job.dataset_id else None

                if not dataset_id_str:
                    raise ValueError("No dataset_id specified in step parameters")

                task_result = await _execute_dataset_operation(
                    uuid.UUID(dataset_id_str),
                    step_type,
                    step_params,
                )

                log_entry.status = "completed"
                log_entry.output = task_result
                log_entry.completed_at = datetime.now(timezone.utc)
                await session.flush()
                step_results.append(task_result)

            except Exception as e:
                log_entry.status = "failed"
                log_entry.error_message = str(e)
                log_entry.completed_at = datetime.now(timezone.utc)
                await session.flush()
                overall_status = "failed"
                break

        await session.execute(
            update(WorkflowJobModel)
            .where(WorkflowJobModel.id == workflow_job_id)
            .values(
                status=overall_status,
                completed_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

        return {
            "workflow_job_id": str(workflow_job_id),
            "status": overall_status,
            "steps_completed": len([s for s in step_results if s]),
            "total_steps": len(steps),
        }


@celery_app.task(bind=True, base=DatabaseTask, name="generate_export")
def generate_export(
    self,
    dataset_id: str,
    fmt: str,
    export_id: str,
) -> dict[str, Any]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _execute_export(uuid.UUID(dataset_id), fmt, uuid.UUID(export_id))
        )
        return result
    finally:
        loop.close()


async def _execute_export(
    dataset_id: uuid.UUID,
    fmt: str,
    export_id: uuid.UUID,
) -> dict[str, Any]:
    from services.export_service import ExportService

    service = ExportService()

    if fmt == "csv":
        data = await service.export_csv(dataset_id)
    elif fmt == "excel":
        data = await service.export_excel(dataset_id)
    elif fmt == "json":
        data = await service.export_json(dataset_id)
    elif fmt == "parquet":
        data = await service.export_parquet(dataset_id)
    else:
        raise ValueError(f"Unsupported export format: {fmt}")

    from core.config import get_settings
    from storage.object_store import ObjectStore

    settings = get_settings()
    store = ObjectStore()
    key = f"exports/{export_id}/{dataset_id}.{fmt}"

    await store.upload_fileobj(key, data, content_type=_get_mime_type(fmt))

    return {
        "export_id": str(export_id),
        "dataset_id": str(dataset_id),
        "format": fmt,
        "storage_key": key,
        "size_bytes": len(data),
    }


def _get_mime_type(fmt: str) -> str:
    return {
        "csv": "text/csv",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json": "application/json",
        "parquet": "application/octet-stream",
    }.get(fmt, "application/octet-stream")
