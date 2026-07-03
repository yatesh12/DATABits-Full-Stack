from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_principal
from api.v1.upload.schemas import (
    MultiUploadResponse,
    MessageResponse,
    UploadResponse,
    UploadStatusResponse,
    UrlUploadRequest,
)
from api.v1.upload.service import (
    create_dataset_from_upload,
    get_upload_status,
    save_upload,
    save_upload_from_url,
)
from models.auth import UserModel

router = APIRouter(tags=["upload"], prefix="/upload")


@router.post("/file", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> UploadResponse:
    upload_info = await save_upload(file, current_user.id)
    dataset = await create_dataset_from_upload(session, current_user, upload_info)
    return UploadResponse(
        upload_id=upload_info["upload_id"],
        filename=upload_info["filename"],
        file_size=upload_info["file_size"],
        mime_type=upload_info["mime_type"],
        status=dataset.status,
        created_at=dataset.created_at,
    )


@router.post("/files", response_model=MultiUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_multiple_files(
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MultiUploadResponse:
    uploads = []
    failed = 0
    for file in files:
        try:
            upload_info = await save_upload(file, current_user.id)
            dataset = await create_dataset_from_upload(session, current_user, upload_info)
            uploads.append(
                UploadResponse(
                    upload_id=upload_info["upload_id"],
                    filename=upload_info["filename"],
                    file_size=upload_info["file_size"],
                    mime_type=upload_info["mime_type"],
                    status=dataset.status,
                    created_at=dataset.created_at,
                )
            )
        except Exception:
            failed += 1
    return MultiUploadResponse(uploads=uploads, failed=failed)


@router.get("/{upload_id}/status", response_model=UploadStatusResponse)
async def get_upload_status_endpoint(
    upload_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> UploadStatusResponse:
    status_info = await get_upload_status(session, upload_id, current_user.id)
    if status_info is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    return UploadStatusResponse(**status_info)


@router.post("/url", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_from_url(
    body: UrlUploadRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> UploadResponse:
    try:
        upload_info = await save_upload_from_url(body.url, body.filename, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")

    dataset = await create_dataset_from_upload(session, current_user, upload_info)
    return UploadResponse(
        upload_id=upload_info["upload_id"],
        filename=upload_info["filename"],
        file_size=upload_info["file_size"],
        mime_type=upload_info["mime_type"],
        status=dataset.status,
        created_at=dataset.created_at,
    )
