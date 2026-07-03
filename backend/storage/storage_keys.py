from __future__ import annotations

import uuid


class StorageKeys:
    @staticmethod
    def dataset_key(tenant_id: uuid.UUID, dataset_id: uuid.UUID, filename: str) -> str:
        return f"tenants/{tenant_id}/datasets/{dataset_id}/{filename}"

    @staticmethod
    def version_key(tenant_id: uuid.UUID, dataset_id: uuid.UUID, version: int) -> str:
        return f"tenants/{tenant_id}/datasets/{dataset_id}/versions/v{version}.parquet"

    @staticmethod
    def temp_key(tenant_id: uuid.UUID, upload_id: str) -> str:
        return f"tenants/{tenant_id}/temp/{upload_id}"

    @staticmethod
    def export_key(tenant_id: uuid.UUID, dataset_id: uuid.UUID, fmt: str) -> str:
        return f"tenants/{tenant_id}/exports/{dataset_id}/export.{fmt}"

    @staticmethod
    def dataset_prefix(tenant_id: uuid.UUID) -> str:
        return f"tenants/{tenant_id}/datasets/"

    @staticmethod
    def temp_prefix(tenant_id: uuid.UUID) -> str:
        return f"tenants/{tenant_id}/temp/"

    @staticmethod
    def export_prefix(tenant_id: uuid.UUID) -> str:
        return f"tenants/{tenant_id}/exports/"
