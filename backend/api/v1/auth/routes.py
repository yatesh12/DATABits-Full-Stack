from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_principal, rate_limit
from api.v1.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutResponse,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    SessionResponse,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from api.v1.auth.service import (
    authenticate_user,
    change_password,
    create_password_reset_token,
    create_session,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_sessions,
    reset_password_with_token,
    revoke_session,
    update_last_login,
    verify_email_token,
)
from core.config import get_settings
from models.auth import UserModel

settings = get_settings()

router = APIRouter(tags=["auth"], prefix="/auth")


def _create_tokens(user_id: str) -> tuple[str, str, int]:
    now = datetime.now(timezone.utc)
    access_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    access_payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + access_expires,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    refresh_payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + refresh_expires,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }

    key = settings.RSA_PRIVATE_KEY or settings.JWT_SECRET
    algorithm = settings.JWT_ALGORITHM if settings.RSA_PRIVATE_KEY else "HS256"

    access_token = jwt.encode(access_payload, key, algorithm=algorithm)
    refresh_token = jwt.encode(refresh_payload, key, algorithm=algorithm)
    return access_token, refresh_token, settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    existing = await get_user_by_email(session, body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    existing = await get_user_by_username(session, body.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")

    user = await create_user(
        session,
        username=body.username,
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        tenant_slug=body.tenant_slug,
    )
    return RegisterResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit),
) -> TokenResponse:
    user = await authenticate_user(session, body.username, body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await update_last_login(session, user.id)

    access_token, refresh_token, expires_in = _create_tokens(str(user.id))

    token_hash = sha256(refresh_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    await create_session(
        session,
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> LogoutResponse:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ")
        token_hash = sha256(token.encode()).hexdigest()
        sessions = await get_user_sessions(session, current_user.id)
        for sess in sessions:
            if sess.token_hash == token_hash:
                await revoke_session(session, sess.id, current_user.id)
                break

    return LogoutResponse()


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserModel = Depends(get_principal),
) -> UserResponse:
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        is_superuser=current_user.is_superuser,
        avatar_url=current_user.avatar_url,
        display_name=current_user.display_name,
        tenant_id=str(current_user.tenant_id) if current_user.tenant_id else None,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=current_user.last_login,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    key = settings.RSA_PUBLIC_KEY or settings.JWT_SECRET
    algorithm = settings.JWT_ALGORITHM if settings.RSA_PUBLIC_KEY else "HS256"
    try:
        payload = jwt.decode(
            body.refresh_token,
            key,
            algorithms=[algorithm],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    token_hash = sha256(body.refresh_token.encode()).hexdigest()
    sessions = await get_user_sessions(session, uuid.UUID(user_id))
    valid_session = any(
        s.token_hash == token_hash and not s.is_revoked and s.expires_at > datetime.now(timezone.utc)
        for s in sessions
    )
    if not valid_session:
        raise HTTPException(status_code=401, detail="Session revoked or expired")

    user = await get_user_by_id(session, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access_token, new_refresh_token, expires_in = _create_tokens(user_id)

    new_token_hash = sha256(new_refresh_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    await create_session(
        session,
        user_id=user.id,
        token_hash=new_token_hash,
        expires_at=expires_at,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=expires_in,
    )


@router.post("/change-password", response_model=MessageResponse)
async def change_password_endpoint(
    body: ChangePasswordRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    success = await change_password(session, current_user, body.current_password, body.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    return MessageResponse(message="Password changed successfully")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit),
) -> MessageResponse:
    user = await get_user_by_email(session, body.email)
    if user is None:
        return MessageResponse(message="If the email exists, a reset link has been sent")

    token = await create_password_reset_token(session, user)
    # TODO: Send email with reset token
    return MessageResponse(message="If the email exists, a reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit),
) -> MessageResponse:
    success = await reset_password_with_token(session, body.token, body.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    return MessageResponse(message="Password reset successfully")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    body: VerifyEmailRequest,
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    success = await verify_email_token(session, body.token)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    return MessageResponse(message="Email verified successfully")


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
    request: Request = None,
) -> list[SessionResponse]:
    sessions = await get_user_sessions(session, current_user.id)
    auth_header = request.headers.get("Authorization", "")
    current_token_hash = None
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ")
        current_token_hash = sha256(token.encode()).hexdigest()

    return [
        SessionResponse(
            id=s.id,
            ip_address=s.ip_address,
            user_agent=s.user_agent,
            device_info=s.device_info,
            created_at=s.created_at,
            expires_at=s.expires_at,
            is_revoked=s.is_revoked,
            is_current=s.token_hash == current_token_hash,
        )
        for s in sessions
    ]


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session_endpoint(
    session_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    success = await revoke_session(session, session_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return MessageResponse(message="Session revoked successfully")
