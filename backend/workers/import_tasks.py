from __future__ import annotations

import uuid
from typing import Any, Optional

from celery import Task
from celery.utils.log import get_task_logger

from workers.celery_app import celery_app

logger = get_task_logger(__name__)


class ImportTask(Task):
    autoretry_for = (Exception,)
    max_retries = 3
    default_retry_delay = 60


@celery_app.task(bind=True, base=ImportTask, name="import_from_url")
def import_from_url(
    self,
    url: str,
    dataset_id: str,
    tenant_id: str,
    file_type: Optional[str] = None,
) -> dict[str, Any]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _execute_url_import(url, uuid.UUID(dataset_id), uuid.UUID(tenant_id), file_type)
        )
        return result
    finally:
        loop.close()


async def _execute_url_import(
    url: str,
    dataset_id: uuid.UUID,
    tenant_id: uuid.UUID,
    file_type: Optional[str] = None,
) -> dict[str, Any]:
    import httpx
    import pandas as pd
    import io

    from storage.dataset_store import LocalDatasetStore
    from core.database import async_session_factory
    from repositories.dataset_repository import DatasetRepository

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(url)
        response.raise_for_status()
        content = response.content

    file_type = file_type or url.split(".")[-1].lower()

    if file_type == "csv":
        df = pd.read_csv(io.BytesIO(content))
    elif file_type == "json":
        df = pd.read_json(io.BytesIO(content))
    elif file_type in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(content))
    elif file_type == "parquet":
        df = pd.read_parquet(io.BytesIO(content))
    elif file_type == "tsv":
        df = pd.read_csv(io.BytesIO(content), sep="\t")
    else:
        df = pd.read_csv(io.BytesIO(content))

    store = LocalDatasetStore()
    await store.save(dataset_id, df)

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

    return {
        "dataset_id": str(dataset_id),
        "source": url,
        "rows": len(df),
        "columns": len(df.columns),
        "status": "imported",
    }


@celery_app.task(bind=True, base=ImportTask, name="import_from_s3")
def import_from_s3(
    self,
    bucket: str,
    key: str,
    dataset_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _execute_s3_import(bucket, key, uuid.UUID(dataset_id), uuid.UUID(tenant_id))
        )
        return result
    finally:
        loop.close()


async def _execute_s3_import(
    bucket: str,
    key: str,
    dataset_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    import pandas as pd
    import io

    from core.config import get_settings
    from storage.dataset_store import LocalDatasetStore
    from core.database import async_session_factory
    from repositories.dataset_repository import DatasetRepository

    settings = get_settings()
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION,
    )

    response = client.get_object(Bucket=bucket, Key=key)
    content = response["Body"].read()

    file_type = key.split(".")[-1].lower()
    if file_type == "csv":
        df = pd.read_csv(io.BytesIO(content))
    elif file_type == "json":
        df = pd.read_json(io.BytesIO(content))
    elif file_type in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(content))
    elif file_type == "parquet":
        df = pd.read_parquet(io.BytesIO(content))
    else:
        df = pd.read_csv(io.BytesIO(content))

    store = LocalDatasetStore()
    await store.save(dataset_id, df)

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

    return {
        "dataset_id": str(dataset_id),
        "source": f"s3://{bucket}/{key}",
        "rows": len(df),
        "columns": len(df.columns),
        "status": "imported",
    }


@celery_app.task(bind=True, base=ImportTask, name="import_from_api")
def import_from_api(
    self,
    source_config: dict[str, Any],
    dataset_id: str,
) -> dict[str, Any]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _execute_api_import(source_config, uuid.UUID(dataset_id))
        )
        return result
    finally:
        loop.close()


async def _execute_api_import(
    source_config: dict[str, Any],
    dataset_id: uuid.UUID,
) -> dict[str, Any]:
    import httpx
    import pandas as pd

    from storage.dataset_store import LocalDatasetStore
    from core.database import async_session_factory
    from repositories.dataset_repository import DatasetRepository

    url = source_config.get("url")
    headers = source_config.get("headers", {})
    params = source_config.get("params", {})
    data_path = source_config.get("data_path")

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        json_data = response.json()

    if data_path:
        for part in data_path.split("."):
            if isinstance(json_data, dict):
                json_data = json_data.get(part, {})
            elif isinstance(json_data, list):
                idx = int(part) if part.isdigit() else 0
                json_data = json_data[idx] if idx < len(json_data) else {}

    if isinstance(json_data, dict):
        df = pd.DataFrame([json_data])
    elif isinstance(json_data, list):
        df = pd.DataFrame(json_data)
    else:
        raise ValueError("Unsupported API response format")

    if df.empty:
        raise ValueError("No data received from API")

    store = LocalDatasetStore()
    await store.save(dataset_id, df)

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

    return {
        "dataset_id": str(dataset_id),
        "source": url,
        "rows": len(df),
        "columns": len(df.columns),
        "status": "imported",
    }


@celery_app.task(bind=True, base=ImportTask, name="process_upload")
def process_upload(
    self,
    upload_id: str,
    dataset_id: str,
) -> dict[str, Any]:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _execute_upload_processing(upload_id, uuid.UUID(dataset_id))
        )
        return result
    finally:
        loop.close()


async def _execute_upload_processing(
    upload_id: str,
    dataset_id: uuid.UUID,
) -> dict[str, Any]:
    import pandas as pd
    from pathlib import Path

    from core.config import get_settings
    from storage.dataset_store import LocalDatasetStore
    from core.database import async_session_factory
    from repositories.dataset_repository import DatasetRepository

    settings = get_settings()
    upload_path = Path(settings.FILE_UPLOAD_DIR) / "uploads" / upload_id

    if not upload_path.exists():
        raise ValueError(f"Upload {upload_id} not found")

    files = list(upload_path.glob("*"))
    if not files:
        raise ValueError(f"No files found in upload {upload_id}")

    file_path = files[0]
    file_type = file_path.suffix.lower()

    if file_type == ".csv":
        df = pd.read_csv(file_path)
    elif file_type in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
    elif file_type == ".json":
        df = pd.read_json(file_path)
    elif file_type == ".parquet":
        df = pd.read_parquet(file_path)
    elif file_type == ".tsv":
        df = pd.read_csv(file_path, sep="\t")
    elif file_type == ".xml":
        df = pd.read_xml(file_path)
    else:
        df = pd.read_csv(file_path)

    store = LocalDatasetStore()
    await store.save(dataset_id, df)

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

    import shutil
    shutil.rmtree(upload_path, ignore_errors=True)

    return {
        "dataset_id": str(dataset_id),
        "upload_id": upload_id,
        "filename": file_path.name,
        "rows": len(df),
        "columns": len(df.columns),
        "status": "processed",
    }
