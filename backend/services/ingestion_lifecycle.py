from __future__ import annotations

import uuid
from typing import Any, Optional

from core.config import get_settings
from core.database import async_session_factory
from models.data_platform import SourceConnectionModel
from repositories.dataset_repository import DatasetRepository
from storage.dataset_store import LocalDatasetStore

settings = get_settings()


class IngestionLifecycleService:
    def __init__(self) -> None:
        self._store = LocalDatasetStore()

    async def create_source_connection(
        self,
        tenant_id: uuid.UUID,
        name: str,
        source_type: str,
        config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        async with async_session_factory() as session:
            connection = SourceConnectionModel(
                tenant_id=tenant_id,
                name=name,
                source_type=source_type,
                config=config or {},
                status="active",
            )
            session.add(connection)
            await session.flush()
            await session.refresh(connection)
            return {
                "id": connection.id,
                "tenant_id": str(connection.tenant_id),
                "name": connection.name,
                "source_type": connection.source_type,
                "config": connection.config,
                "status": connection.status,
                "created_at": connection.created_at.isoformat() if connection.created_at else None,
            }

    async def trigger_sync(
        self,
        connection_id: int,
        dataset_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        from celery import chain as celery_chain
        from workers.tasks import process_dataset_task

        task = process_dataset_task.delay(
            dataset_id=str(dataset_id),
            operation="ingest",
            params={"connection_id": connection_id, "user_id": str(user_id)},
        )

        return {
            "task_id": task.id,
            "dataset_id": str(dataset_id),
            "connection_id": connection_id,
            "status": "triggered",
        }

    async def get_job_status(self, job_id: uuid.UUID) -> Optional[dict[str, Any]]:
        from celery.result import AsyncResult
        from workers.celery_app import celery_app

        result = AsyncResult(str(job_id), app=celery_app)
        return {
            "task_id": job_id,
            "status": result.status,
            "result": result.result if result.ready() else None,
        }

    async def process_source_data(
        self,
        source_type: str,
        source_config: dict[str, Any],
        dataset_id: uuid.UUID,
    ) -> pd.DataFrame:
        import pandas as pd

        if source_type == "csv":
            file_path = source_config.get("file_path")
            df = pd.read_csv(file_path)
        elif source_type == "excel":
            file_path = source_config.get("file_path")
            sheet_name = source_config.get("sheet_name", 0)
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        elif source_type == "json":
            file_path = source_config.get("file_path")
            df = pd.read_json(file_path)
        elif source_type == "parquet":
            file_path = source_config.get("file_path")
            df = pd.read_parquet(file_path)
        elif source_type == "api":
            import httpx

            url = source_config.get("url")
            headers = source_config.get("headers", {})
            response = httpx.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            df = pd.DataFrame(data)
        elif source_type == "url":
            import httpx

            url = source_config.get("url")
            response = httpx.get(url, timeout=30)
            response.raise_for_status()
            import io

            content = response.content
            if url.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(content))
            elif url.endswith(".json"):
                df = pd.read_json(io.BytesIO(content))
            elif url.endswith(".parquet"):
                df = pd.read_parquet(io.BytesIO(content))
            else:
                df = pd.read_csv(io.BytesIO(content))
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

        if df.empty:
            raise ValueError("No data extracted from source")

        await self._store.save(dataset_id, df)

        async with async_session_factory() as session:
            repo = DatasetRepository(session)
            await repo.update(
                dataset_id,
                {
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "status": "ready",
                    "columns_meta": [{"name": col, "dtype": str(df[col].dtype)} for col in df.columns],
                },
            )

        return df
