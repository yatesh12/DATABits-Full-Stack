from __future__ import annotations

from typing import Any, Optional

from core.config import get_settings
from storage.dataset_store import LocalDatasetStore

settings = get_settings()


class S3DatasetStore:
    def __init__(self) -> None:
        import boto3
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
            use_ssl=settings.S3_USE_SSL,
        )
        self._bucket = settings.S3_BUCKET_NAME

    async def save(
        self,
        dataset_id: str,
        dataframe: Any,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        import io
        import json
        import pandas as pd

        buffer = io.BytesIO()
        pd.DataFrame(dataframe).to_parquet(buffer, index=False)
        buffer.seek(0)
        self._client.put_object(
            Bucket=self._bucket,
            Key=f"datasets/{dataset_id}.parquet",
            Body=buffer.getvalue(),
        )
        if metadata:
            self._client.put_object(
                Bucket=self._bucket,
                Key=f"datasets/{dataset_id}_meta.json",
                Body=json.dumps(metadata, default=str),
            )

    async def load(self, dataset_id: str) -> Any:
        import io
        import pandas as pd

        try:
            response = self._client.get_object(
                Bucket=self._bucket,
                Key=f"datasets/{dataset_id}.parquet",
            )
            return pd.read_parquet(io.BytesIO(response["Body"].read()))
        except self._client.exceptions.NoSuchKey:
            return None

    async def delete(self, dataset_id: str) -> bool:
        try:
            self._client.delete_objects(
                Bucket=self._bucket,
                Delete={
                    "Objects": [
                        {"Key": f"datasets/{dataset_id}.parquet"},
                        {"Key": f"datasets/{dataset_id}_meta.json"},
                    ]
                },
            )
            return True
        except Exception:
            return False

    async def list(self) -> list[dict[str, Any]]:
        response = self._client.list_objects_v2(
            Bucket=self._bucket,
            Prefix="datasets/",
        )
        datasets = []
        for obj in response.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".parquet"):
                datasets.append({
                    "dataset_id": key.split("/")[-1].replace(".parquet", ""),
                    "size_bytes": obj["Size"],
                })
        return datasets


class TigrisDatasetStore(S3DatasetStore):
    def __init__(self) -> None:
        import boto3
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT or "https://fly.storage.tigris.dev",
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
            use_ssl=True,
        )
        self._bucket = settings.S3_BUCKET_NAME


class DatasetStoreFactory:
    _stores: dict[str, type] = {
        "local": LocalDatasetStore,
        "s3": S3DatasetStore,
        "tigris": TigrisDatasetStore,
    }

    @classmethod
    def get_store(cls, backend_type: str = "local") -> Any:
        store_class = cls._stores.get(backend_type)
        if store_class is None:
            raise ValueError(f"Unknown storage backend: {backend_type}. Supported: {list(cls._stores.keys())}")
        if backend_type == "local":
            return store_class()
        return store_class()

    @classmethod
    def register_store(cls, name: str, store_class: type) -> None:
        cls._stores[name] = store_class
