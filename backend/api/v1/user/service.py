from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.auth import UserModel
from models.platform import ProjectHistoryModel, UserSettingModel


async def get_user_profile(session: AsyncSession, user_id: uuid.UUID) -> UserModel | None:
    result = await session.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    return result.scalar_one_or_none()


async def update_user_profile(
    session: AsyncSession,
    user: UserModel,
    updates: dict[str, Any],
) -> UserModel:
    for key, value in updates.items():
        setattr(user, key, value)
    user.updated_at = datetime.now(timezone.utc)
    session.add(user)
    await session.flush()
    return user


async def get_user_settings(
    session: AsyncSession, user_id: uuid.UUID
) -> list[UserSettingModel]:
    result = await session.execute(
        select(UserSettingModel)
        .where(UserSettingModel.user_id == user_id)
        .order_by(UserSettingModel.key)
    )
    return list(result.scalars().all())


async def update_user_settings(
    session: AsyncSession,
    user_id: uuid.UUID,
    settings_dict: dict[str, Any],
) -> list[UserSettingModel]:
    for key, value in settings_dict.items():
        result = await session.execute(
            select(UserSettingModel).where(
                UserSettingModel.user_id == user_id,
                UserSettingModel.key == key,
            )
        )
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
            setting.updated_at = datetime.now(timezone.utc)
            session.add(setting)
        else:
            new_setting = UserSettingModel(
                user_id=user_id,
                key=key,
                value=value,
            )
            session.add(new_setting)
    await session.flush()
    return await get_user_settings(session, user_id)


async def delete_user_account(
    session: AsyncSession, user: UserModel
) -> None:
    await session.delete(user)
    await session.flush()


async def get_user_activity(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[ProjectHistoryModel]:
    result = await session.execute(
        select(ProjectHistoryModel)
        .where(ProjectHistoryModel.user_id == user_id)
        .order_by(ProjectHistoryModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())
