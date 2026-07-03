from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_principal
from api.v1.user.schemas import (
    ActivityResponse,
    MessageResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    SettingResponse,
    SettingsUpdateRequest,
)
from api.v1.user.service import (
    delete_user_account,
    get_user_activity,
    get_user_profile,
    get_user_settings,
    update_user_profile,
    update_user_settings,
)
from models.auth import UserModel

router = APIRouter(tags=["user"], prefix="/user")


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: UserModel = Depends(get_principal),
) -> ProfileResponse:
    return ProfileResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=current_user.last_login,
    )


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> ProfileResponse:
    updates = body.model_dump(exclude_unset=True)
    user = await update_user_profile(session, current_user, updates)
    return ProfileResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        is_verified=user.is_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
    )


@router.get("/settings", response_model=list[SettingResponse])
async def get_settings(
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[SettingResponse]:
    settings = await get_user_settings(session, current_user.id)
    return [
        SettingResponse(
            key=s.key,
            value=s.value,
            updated_at=s.updated_at,
        )
        for s in settings
    ]


@router.patch("/settings", response_model=list[SettingResponse])
async def update_settings(
    body: SettingsUpdateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[SettingResponse]:
    settings = await update_user_settings(session, current_user.id, body.settings)
    return [
        SettingResponse(
            key=s.key,
            value=s.value,
            updated_at=s.updated_at,
        )
        for s in settings
    ]


@router.delete("/account", response_model=MessageResponse)
async def delete_account(
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    await delete_user_account(session, current_user)
    return MessageResponse(message="Account deleted successfully")


@router.get("/activity", response_model=list[ActivityResponse])
async def get_activity(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[ActivityResponse]:
    activities = await get_user_activity(session, current_user.id, limit, offset)
    return [
        ActivityResponse(
            id=a.id,
            action=a.action,
            entity_type=a.entity_type,
            entity_id=a.entity_id,
            details=a.changes,
            created_at=a.created_at,
        )
        for a in activities
    ]
