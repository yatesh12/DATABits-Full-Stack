from __future__ import annotations

import io
from typing import Any, Optional

from core.config import get_settings

settings = get_settings()


class ObjectStore:
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: Optional[str] = None,
        bucket: Optional[str] = None,
    ) -> None:
        import boto3

        self._endpoint = endpoint_url or settings.S3_ENDPOINT
        self._access_key = access_key or settings.S3_ACCESS_KEY_ID
        self._secret_key = secret_key or settings.S3_SECRET_ACCESS_KEY
        self._region = region or settings.S3_REGION
        self._bucket = bucket or settings.S3_BUCKET_NAME

        self._client = boto3.client(
            "s3",
            endpoint_url=self._endpoint,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            region_name=self._region,
            use_ssl=True,
        )

    async def get_files(self, prefix: str = "") -> list[dict[str, Any]]:
        response = self._client.list_objects_v2(
            Bucket=self._bucket,
            Prefix=prefix,
        )
        files = []
        for obj in response.get("Contents", []):
            files.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "etag": obj.get("ETag", ""),
                "last_modified": obj["LastModified"].isoformat() if obj.get("LastModified") else None,
            })
        return files

    async def get_file_metadata(self, key: str) -> dict[str, Any]:
        response = self._client.head_object(Bucket=self._bucket, Key=key)
        return {
            "key": key,
            "size": response["ContentLength"],
            "content_type": response.get("ContentType", ""),
            "etag": response.get("ETag", ""),
            "last_modified": response["LastModified"].isoformat() if response.get("LastModified") else None,
            "metadata": response.get("Metadata", {}),
        }

    async def copy_file(self, source_key: str, dest_key: str) -> dict[str, Any]:
        copy_source = {"Bucket": self._bucket, "Key": source_key}
        self._client.copy_object(
            Bucket=self._bucket,
            CopySource=copy_source,
            Key=dest_key,
        )
        return {
            "source_key": source_key,
            "destination_key": dest_key,
            "bucket": self._bucket,
        }

    async def upload_fileobj(
        self,
        key: str,
        data: bytes,
        content_type: Optional[str] = None,
    ) -> dict[str, Any]:
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            **extra_args,
        )
        return {
            "key": key,
            "bucket": self._bucket,
            "size_bytes": len(data),
        }

    async def download_fileobj(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    async def delete_file(self, key: str) -> bool:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    async def file_exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    async def generate_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "get_object",
    ) -> str:
        return self._client.generate_presigned_url(
            method,
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
