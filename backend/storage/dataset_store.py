from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from core.config import get_settings

settings = get_settings()


class LocalDatasetStore:
    def __init__(self, base_path: Optional[Path] = None) -> None:
        self._base_path = base_path or Path(settings.FILE_UPLOAD_DIR) / "datasets"
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _dataset_path(self, dataset_id: uuid.UUID) -> Path:
        return self._base_path / f"{dataset_id}.parquet"

    def _metadata_path(self, dataset_id: uuid.UUID) -> Path:
        return self._base_path / f"{dataset_id}_meta.json"

    async def save(
        self,
        dataset_id: uuid.UUID,
        dataframe: pd.DataFrame,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        path = self._dataset_path(dataset_id)
        dataframe.to_parquet(path, index=False)

        if metadata:
            import json
            meta_path = self._metadata_path(dataset_id)
            meta_path.write_text(json.dumps(metadata, default=str))

    async def load(self, dataset_id: uuid.UUID) -> Optional[pd.DataFrame]:
        path = self._dataset_path(dataset_id)
        if not path.exists():
            return None
        return pd.read_parquet(path)

    async def delete(self, dataset_id: uuid.UUID) -> bool:
        path = self._dataset_path(dataset_id)
        meta_path = self._metadata_path(dataset_id)
        deleted = False

        if path.exists():
            path.unlink()
            deleted = True
        if meta_path.exists():
            meta_path.unlink()

        return deleted

    async def list(self) -> list[dict[str, Any]]:
        datasets = []
        for path in self._base_path.glob("*.parquet"):
            dataset_id = path.stem
            meta_path = self._base_path / f"{dataset_id}_meta.json"
            metadata = {}
            if meta_path.exists():
                import json
                metadata = json.loads(meta_path.read_text())
            datasets.append({
                "dataset_id": dataset_id,
                "size_bytes": path.stat().st_size,
                "metadata": metadata,
            })
        return datasets
