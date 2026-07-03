from __future__ import annotations

import io
import uuid
from typing import Any, Optional

import pandas as pd

from core.config import get_settings
from storage.dataset_store import LocalDatasetStore

settings = get_settings()


class ExportService:
    def __init__(self) -> None:
        self._store = LocalDatasetStore()

    async def _load_dataframe(self, dataset_id: uuid.UUID) -> pd.DataFrame:
        df = await self._store.load(dataset_id)
        if df is None:
            raise ValueError(f"Dataset {dataset_id} not found")
        return df

    async def export_csv(self, dataset_id: uuid.UUID) -> bytes:
        df = await self._load_dataframe(dataset_id)
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        return buffer.getvalue()

    async def export_excel(self, dataset_id: uuid.UUID) -> bytes:
        df = await self._load_dataframe(dataset_id)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Data")
        buffer.seek(0)
        return buffer.getvalue()

    async def export_json(self, dataset_id: uuid.UUID, orient: str = "records") -> bytes:
        df = await self._load_dataframe(dataset_id)
        buffer = io.BytesIO()
        buffer.write(df.to_json(orient=orient).encode("utf-8"))
        buffer.seek(0)
        return buffer.getvalue()

    async def export_parquet(self, dataset_id: uuid.UUID) -> bytes:
        df = await self._load_dataframe(dataset_id)
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False)
        buffer.seek(0)
        return buffer.getvalue()

    async def export_to_s3(
        self,
        dataset_id: uuid.UUID,
        bucket: str,
        key: str,
        fmt: str = "parquet",
    ) -> dict[str, Any]:
        import boto3

        df = await self._load_dataframe(dataset_id)
        buffer = io.BytesIO()

        if fmt == "csv":
            df.to_csv(buffer, index=False)
        elif fmt == "json":
            buffer.write(df.to_json(orient="records").encode("utf-8"))
        elif fmt == "parquet":
            df.to_parquet(buffer, index=False)
        else:
            raise ValueError(f"Unsupported export format: {fmt}")

        buffer.seek(0)

        client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
            use_ssl=settings.S3_USE_SSL,
        )
        client.put_object(Bucket=bucket, Key=key, Body=buffer.getvalue())

        return {
            "bucket": bucket,
            "key": key,
            "dataset_id": str(dataset_id),
            "format": fmt,
            "size_bytes": buffer.tell(),
        }
