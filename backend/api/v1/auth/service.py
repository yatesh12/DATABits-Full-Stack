from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from models.auth import (
    PasswordResetModel,
    SessionModel,
    UserModel,
)

settings = get_settings()


async def create_user(
    session: AsyncSession,
    username: str,
    email: str,
    password: str,
    display_name: str | None = None,
    tenant_slug: str | None = None,
) -> UserModel:
    user = UserModel(
        username=username,
        email=email,
        display_name=display_name,
    )
    user.set_password(password)
    session.add(user)
    await session.flush()
    return user


async def get_user_by_email(session: AsyncSession, email: str) -> UserModel | None:
    result = await session.execute(
        select(UserModel).where(UserModel.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_username(session: AsyncSession, username: str) -> UserModel | None:
    result = await session.execute(
        select(UserModel).where(UserModel.username == username)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> UserModel | None:
    result = await session.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    return result.scalar_one_or_none()


async def authenticate_user(
    session: AsyncSession, username: str | None, email: str | None, password: str
) -> UserModel | None:
    user = None
    if username:
        user = await get_user_by_username(session, username)
    elif email:
        user = await get_user_by_email(session, email)

    if user is None or not user.is_active:
        return None
    if not user.verify_password(password):
        return None

    return user


async def update_last_login(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(
        update(UserModel)
        .where(UserModel.id == user_id)
        .values(last_login=datetime.now(timezone.utc))
    )
    await session.flush()


async def change_password(
    session: AsyncSession, user: UserModel, current_password: str, new_password: str
) -> bool:
    if not user.verify_password(current_password):
        return False
    user.set_password(new_password)
    session.add(user)
    await session.flush()
    return True


async def create_password_reset_token(session: AsyncSession, user: UserModel) -> str:
    import secrets
    from hashlib import sha256

    token = secrets.token_urlsafe(48)
    token_hash = sha256(token.encode()).hexdigest()
    reset = PasswordResetModel(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    session.add(reset)
    await session.flush()
    return token


async def reset_password_with_token(
    session: AsyncSession, token: str, new_password: str
) -> bool:
    from hashlib import sha256

    token_hash = sha256(token.encode()).hexdigest()
    result = await session.execute(
        select(PasswordResetModel).where(
            PasswordResetModel.token_hash == token_hash,
            PasswordResetModel.used_at.is_(None),
            PasswordResetModel.expires_at > datetime.now(timezone.utc),
        )
    )
    reset = result.scalar_one_or_none()
    if reset is None:
        return False

    user = await get_user_by_id(session, reset.user_id)
    if user is None:
        return False

    user.set_password(new_password)
    session.add(user)
    reset.used_at = datetime.now(timezone.utc)
    session.add(reset)
    await session.flush()
    return True


async def create_session(
    session: AsyncSession,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
    ip_address: str | None = None,
    user_agent: str | None = None,
    device_info: dict | None = None,
) -> SessionModel:
    sess = SessionModel(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
        device_info=device_info,
    )
    session.add(sess)
    await session.flush()
    return sess


async def revoke_session(session: AsyncSession, session_id: int, user_id: uuid.UUID) -> bool:
    result = await session.execute(
        select(SessionModel).where(
            SessionModel.id == session_id,
            SessionModel.user_id == user_id,
        )
    )
    sess = result.scalar_one_or_none()
    if sess is None:
        return False
    sess.is_revoked = True
    session.add(sess)
    await session.flush()
    return True


async def revoke_all_user_sessions(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(
        update(SessionModel)
        .where(
            SessionModel.user_id == user_id,
            SessionModel.is_revoked == False,
        )
        .values(is_revoked=True)
    )
    await session.flush()


async def get_user_sessions(
    session: AsyncSession, user_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> list[SessionModel]:
    result = await session.execute(
        select(SessionModel)
        .where(SessionModel.user_id == user_id)
        .order_by(SessionModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def verify_email_token(session: AsyncSession, token: str) -> bool:
    from hashlib import sha256

    token_hash = sha256(token.encode()).hexdigest()
    result = await session.execute(
        select(PasswordResetModel).where(
            PasswordResetModel.token_hash == token_hash,
            PasswordResetModel.used_at.is_(None),
            PasswordResetModel.expires_at > datetime.now(timezone.utc),
        )
    )
    reset = result.scalar_one_or_none()
    if reset is None:
        return False

    user = await get_user_by_id(session, reset.user_id)
    if user is None:
        return False

    user.is_verified = True
    session.add(user)
    reset.used_at = datetime.now(timezone.utc)
    session.add(reset)
    await session.flush()
    return True
