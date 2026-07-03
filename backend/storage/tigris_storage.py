from __future__ import annotations

from typing import Any, Optional

from core.config import get_settings

settings = get_settings()

TIGRIS_ENDPOINT = "https://fly.storage.tigris.dev"


class TigrisStorage:
    def __init__(self) -> None:
        import boto3
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT or TIGRIS_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
            use_ssl=True,
        )

    async def upload_file(
        self,
        bucket: str,
        key: str,
        file_bytes: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        extra_args: dict[str, Any] = {}
        if content_type:
            extra_args["ContentType"] = content_type
        if metadata:
            extra_args["Metadata"] = metadata

        self._client.put_object(
            Bucket=bucket,
            Key=key,
            Body=file_bytes,
            **extra_args,
        )
        return {
            "bucket": bucket,
            "key": key,
            "size_bytes": len(file_bytes),
        }

    async def download_file(self, bucket: str, key: str) -> bytes:
        response = self._client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    async def delete_file(self, bucket: str, key: str) -> bool:
        try:
            self._client.delete_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False

    async def list_files(
        self,
        bucket: str,
        prefix: str = "",
    ) -> list[dict[str, Any]]:
        response = self._client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        files = []
        for obj in response.get("Contents", []):
            files.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "etag": obj.get("ETag", ""),
                "last_modified": obj["LastModified"].isoformat() if obj.get("LastModified") else None,
            })
        return files

    async def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        from botocore.config import Config as BotoConfig

        config = BotoConfig(signature_version="s3v4")
        client = self._client
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url
