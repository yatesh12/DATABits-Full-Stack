from __future__ import annotations

import uuid
from typing import Any, Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder

from core.database import async_session_factory
from repositories.dataset_repository import DatasetRepository
from storage.dataset_store import LocalDatasetStore


class DatasetService:
    def __init__(self) -> None:
        self._store = LocalDatasetStore()

    async def get(self, dataset_id: uuid.UUID) -> Optional[dict[str, Any]]:
        async with async_session_factory() as session:
            repo = DatasetRepository(session)
            dataset = await repo.get(dataset_id)
            if dataset is None:
                return None
            return dataset.to_dict() if hasattr(dataset, "to_dict") else self._model_to_dict(dataset)

    async def list(
        self,
        tenant_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        async with async_session_factory() as session:
            repo = DatasetRepository(session)
            datasets = await repo.get_by_tenant(tenant_id, skip=skip, limit=limit, status=status)
            return [d.to_dict() if hasattr(d, "to_dict") else self._model_to_dict(d) for d in datasets]

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        async with async_session_factory() as session:
            repo = DatasetRepository(session)
            dataset = await repo.create(data)
            return dataset.to_dict() if hasattr(dataset, "to_dict") else self._model_to_dict(dataset)

    async def update(self, dataset_id: uuid.UUID, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        async with async_session_factory() as session:
            repo = DatasetRepository(session)
            dataset = await repo.update(dataset_id, data)
            if dataset is None:
                return None
            return dataset.to_dict() if hasattr(dataset, "to_dict") else self._model_to_dict(dataset)

    async def delete(self, dataset_id: uuid.UUID) -> bool:
        async with async_session_factory() as session:
            repo = DatasetRepository(session)
            deleted = await repo.delete(dataset_id)
            if deleted:
                await self._store.delete(dataset_id)
            return deleted

    async def handle_missing_values(
        self,
        dataset_id: uuid.UUID,
        strategy: str = "drop",
        columns: Optional[list[str]] = None,
        fill_value: Optional[Any] = None,
    ) -> pd.DataFrame:
        df = await self._store.load(dataset_id)
        if df is None or df.empty:
            raise ValueError("Dataset not found or empty")

        target_cols = columns if columns else df.columns

        for col in target_cols:
            if col not in df.columns:
                continue
            if strategy == "drop":
                df = df.dropna(subset=[col])
            elif strategy == "mean":
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].fillna(df[col].mean())
            elif strategy == "median":
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].fillna(df[col].median())
            elif strategy == "mode":
                mode_val = df[col].mode()
                if not mode_val.empty:
                    df[col] = df[col].fillna(mode_val[0])
            elif strategy == "constant":
                df[col] = df[col].fillna(fill_value or 0)
            elif strategy == "ffill":
                df[col] = df[col].ffill()
            elif strategy == "bfill":
                df[col] = df[col].bfill()

        meta = {"row_count": len(df), "column_count": len(df.columns)}
        await self._store.save(dataset_id, df)
        return df

    async def normalize(
        self,
        dataset_id: uuid.UUID,
        method: str = "standard",
        columns: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        df = await self._store.load(dataset_id)
        if df is None or df.empty:
            raise ValueError("Dataset not found or empty")

        target_cols = [c for c in (columns or df.columns) if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
        if not target_cols:
            raise ValueError("No numeric columns found for normalization")

        data = df[target_cols].values
        if method == "standard":
            scaler = StandardScaler()
        elif method == "minmax":
            scaler = MinMaxScaler()
        else:
            raise ValueError(f"Unknown normalization method: {method}")

        scaled = scaler.fit_transform(data)
        df[target_cols] = scaled

        await self._store.save(dataset_id, df)
        return df

    async def encode_categorical(
        self,
        dataset_id: uuid.UUID,
        method: str = "label",
        columns: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        df = await self._store.load(dataset_id)
        if df is None or df.empty:
            raise ValueError("Dataset not found or empty")

        target_cols = [
            c for c in (columns or df.columns)
            if c in df.columns and (
                pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_categorical_dtype(df[c])
            )
        ]
        if not target_cols:
            raise ValueError("No categorical columns found")

        if method == "label":
            for col in target_cols:
                df[col] = LabelEncoder().fit_transform(df[col].astype(str))
        elif method == "onehot":
            df = pd.get_dummies(df, columns=target_cols, drop_first=True)
        else:
            raise ValueError(f"Unknown encoding method: {method}")

        await self._store.save(dataset_id, df)
        return df

    async def detect_outliers(
        self,
        dataset_id: uuid.UUID,
        method: str = "zscore",
        threshold: float = 3.0,
        columns: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        df = await self._store.load(dataset_id)
        if df is None or df.empty:
            raise ValueError("Dataset not found or empty")

        target_cols = [c for c in (columns or df.columns) if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
        outlier_indices: set[int] = set()

        for col in target_cols:
            if method == "zscore":
                z = np.abs((df[col] - df[col].mean()) / df[col].std())
                outlier_indices.update(df[z > threshold].index.tolist())
            elif method == "iqr":
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                mask = (df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR))
                outlier_indices.update(df[mask].index.tolist())

        return {
            "total_outliers": len(outlier_indices),
            "outlier_indices": sorted(outlier_indices),
            "columns_analyzed": target_cols,
            "method": method,
            "threshold": threshold,
        }

    async def find_duplicates(
        self,
        dataset_id: uuid.UUID,
        columns: Optional[list[str]] = None,
        keep: str = "first",
    ) -> dict[str, Any]:
        df = await self._store.load(dataset_id)
        if df is None or df.empty:
            raise ValueError("Dataset not found or empty")

        subset = columns if columns else None
        duplicates = df[df.duplicated(subset=subset, keep=keep)]
        return {
            "total_duplicates": len(duplicates),
            "duplicate_indices": duplicates.index.tolist(),
            "columns_considered": subset or list(df.columns),
        }

    async def compute_correlation(
        self,
        dataset_id: uuid.UUID,
        method: str = "pearson",
        columns: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        df = await self._store.load(dataset_id)
        if df is None or df.empty:
            raise ValueError("Dataset not found or empty")

        target_cols = [c for c in (columns or df.columns) if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
        if len(target_cols) < 2:
            raise ValueError("Need at least 2 numeric columns for correlation")

        corr_matrix = df[target_cols].corr(method=method)
        return {
            "method": method,
            "matrix": corr_matrix.to_dict(),
            "columns": target_cols,
        }

    async def export(self, dataset_id: uuid.UUID) -> pd.DataFrame:
        df = await self._store.load(dataset_id)
        if df is None:
            raise ValueError("Dataset not found")
        return df

    async def reset(self, dataset_id: uuid.UUID) -> pd.DataFrame:
        df = await self._store.load(dataset_id)
        if df is None:
            raise ValueError("Dataset not found")
        return df

    async def get_history(self, dataset_id: uuid.UUID) -> list[dict[str, Any]]:
        async with async_session_factory() as session:
            repo = DatasetRepository(session)
            history = await repo.get_processing_history(dataset_id)
            return [
                {
                    "id": h.id,
                    "status": h.status,
                    "source_type": h.source_type,
                    "files_processed": h.files_processed,
                    "rows_ingested": h.rows_ingested,
                    "error_message": h.error_message,
                    "started_at": h.started_at.isoformat() if h.started_at else None,
                    "completed_at": h.completed_at.isoformat() if h.completed_at else None,
                    "created_at": h.created_at.isoformat() if h.created_at else None,
                }
                for h in history
            ]

    async def get_versions(self, dataset_id: uuid.UUID) -> list[dict[str, Any]]:
        async with async_session_factory() as session:
            repo = DatasetRepository(session)
            versions = await repo.get_versions(dataset_id)
            return [
                {
                    "id": v.id,
                    "version_number": v.version_number,
                    "file_size": v.file_size,
                    "row_count": v.row_count,
                    "column_count": v.column_count,
                    "changes_summary": v.changes_summary,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                }
                for v in versions
            ]

    async def create_version(
        self,
        dataset_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        async with async_session_factory() as session:
            repo = DatasetRepository(session)
            version = await repo.create_version(dataset_id, data)
            return {
                "id": version.id,
                "dataset_id": str(version.dataset_id),
                "version_number": version.version_number,
                "file_size": version.file_size,
                "row_count": version.row_count,
                "column_count": version.column_count,
                "changes_summary": version.changes_summary,
                "created_at": version.created_at.isoformat() if version.created_at else None,
            }

    def _model_to_dict(self, model: Any) -> dict[str, Any]:
        return {c.name: getattr(model, c.name) for c in model.__table__.columns}
