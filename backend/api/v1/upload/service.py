from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from models.auth import UserModel
from models.data_platform import DatasetModel

settings = get_settings()

UPLOAD_DIR = Path(settings.FILE_UPLOAD_DIR)
ALLOWED_EXTENSIONS = set(settings.FILE_UPLOAD_ALLOWED_EXTENSIONS)
MAX_FILE_SIZE = settings.FILE_UPLOAD_MAX_SIZE


async def ensure_upload_dir() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def validate_file(filename: str, file_size: int) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File extension '{ext}' is not allowed. Allowed: {ALLOWED_EXTENSIONS}")
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File size exceeds maximum allowed ({MAX_FILE_SIZE / 1024 / 1024:.0f} MB)")


async def save_upload(file: UploadFile, user_id: uuid.UUID) -> dict[str, Any]:
    await ensure_upload_dir()
    contents = await file.read()
    file_size = len(contents)

    validate_file(file.filename or "unknown", file_size)

    upload_id = str(uuid.uuid4())
    ext = Path(file.filename or "csv").suffix
    storage_name = f"{upload_id}{ext}"
    storage_path = UPLOAD_DIR / storage_name

    async with aiofiles.open(storage_path, "wb") as f:
        await f.write(contents)

    return {
        "upload_id": upload_id,
        "filename": file.filename or "unknown",
        "file_size": file_size,
        "mime_type": file.content_type or "application/octet-stream",
        "storage_path": str(storage_path),
        "storage_backend": "local",
    }


async def save_upload_from_url(url: str, filename: str | None, user_id: uuid.UUID) -> dict[str, Any]:
    import httpx

    await ensure_upload_dir()
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True, timeout=60)
        response.raise_for_status()
        contents = response.content

    content_type = response.headers.get("content-type", "application/octet-stream")
    if not filename:
        filename = url.split("/")[-1] or "download"
        if "?" in filename:
            filename = filename.split("?")[0]

    file_size = len(contents)
    validate_file(filename, file_size)

    upload_id = str(uuid.uuid4())
    ext = Path(filename).suffix
    storage_name = f"{upload_id}{ext}"
    storage_path = UPLOAD_DIR / storage_name

    async with aiofiles.open(storage_path, "wb") as f:
        await f.write(contents)

    return {
        "upload_id": upload_id,
        "filename": filename,
        "file_size": file_size,
        "mime_type": content_type,
        "storage_path": str(storage_path),
        "storage_backend": "local",
    }


async def create_dataset_from_upload(
    session: AsyncSession,
    user: UserModel,
    upload_info: dict[str, Any],
) -> DatasetModel:
    dataset = DatasetModel(
        user_id=user.id,
        tenant_id=user.tenant_id,
        name=Path(upload_info["filename"]).stem,
        original_filename=upload_info["filename"],
        file_size=upload_info["file_size"],
        mime_type=upload_info["mime_type"],
        storage_path=upload_info["storage_path"],
        storage_backend=upload_info["storage_backend"],
        status="uploaded",
    )
    session.add(dataset)
    await session.flush()
    return dataset


async def get_upload_status(
    session: AsyncSession, upload_id: str, user_id: uuid.UUID
) -> dict[str, Any] | None:
    # In production, this would check upload tracking table
    result = await session.execute(
        select(DatasetModel).where(
            DatasetModel.storage_path.contains(upload_id),
            DatasetModel.user_id == user_id,
        )
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        return None
    return {
        "upload_id": upload_id,
        "filename": dataset.original_filename or "unknown",
        "status": dataset.status,
        "progress": 100.0 if dataset.status in ("uploaded", "ready", "processing") else None,
        "error_message": dataset.error_message,
        "dataset_id": str(dataset.id),
    }
