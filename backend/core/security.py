from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import jwt
from passlib.context import CryptContext

from core.config import get_settings

settings = get_settings()

_pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__time_cost=3,
    argon2__memory_cost=65536,
    argon2__parallelism=4,
    argon2__hash_len=32,
)


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def _load_private_key() -> Optional[str]:
    key = settings.RSA_PRIVATE_KEY
    if key:
        return key
    return None


def _load_public_key() -> Optional[str]:
    key = settings.RSA_PUBLIC_KEY
    if key:
        return key
    return None


def _get_sign_key() -> str:
    private_key = _load_private_key()
    if private_key:
        return private_key
    return settings.JWT_SECRET


def _get_verify_key() -> str:
    public_key = _load_public_key()
    if public_key:
        return public_key
    return settings.JWT_SECRET


def _get_algorithm() -> str:
    if _load_private_key():
        return "RS256"
    return "HS256"


def create_access_token(
    user_id: str,
    tenant_id: Optional[str] = None,
    scopes: Optional[list[str]] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "jti": uuid.uuid4().hex,
        "type": "access",
    }
    if tenant_id:
        payload["tenant_id"] = tenant_id
    if scopes:
        payload["scopes"] = scopes
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        _get_sign_key(),
        algorithm=_get_algorithm(),
    )


def create_refresh_token(
    user_id: str,
    tenant_id: Optional[str] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "jti": uuid.uuid4().hex,
        "type": "refresh",
    }
    if tenant_id:
        payload["tenant_id"] = tenant_id

    return jwt.encode(
        payload,
        _get_sign_key(),
        algorithm=_get_algorithm(),
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            _get_verify_key(),
            algorithms=[_get_algorithm(), "RS256", "HS256"],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            options={
                "verify_exp": True,
                "verify_iat": True,
                "require": ["sub", "exp", "iat", "type"],
            },
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidAudienceError:
        raise ValueError("Invalid audience")
    except jwt.InvalidIssuerError:
        raise ValueError("Invalid issuer")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}")


def create_token_pair(
    user_id: str,
    tenant_id: Optional[str] = None,
    scopes: Optional[list[str]] = None,
) -> dict[str, str]:
    return {
        "access_token": create_access_token(user_id, tenant_id, scopes),
        "refresh_token": create_refresh_token(user_id, tenant_id),
        "token_type": "bearer",
    }
