from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.auth import UserModel
from repositories.base import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserModel)

    async def get_by_username(self, username: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.username == username)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_tenant(self, tenant_id: uuid.UUID) -> list[UserModel]:
        stmt = (
            select(UserModel)
            .where(UserModel.tenant_id == tenant_id)
            .order_by(UserModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def search(self, query: str) -> list[UserModel]:
        pattern = f"%{query}%"
        stmt = (
            select(UserModel)
            .where(
                or_(
                    UserModel.username.ilike(pattern),
                    UserModel.email.ilike(pattern),
                    UserModel.display_name.ilike(pattern),
                )
            )
            .order_by(UserModel.username)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(last_login=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)
        await self._session.flush()
