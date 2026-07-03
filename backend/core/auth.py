from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.security import decode_token

logger = logging.getLogger(__name__)


@dataclass
class Principal:
    id: str
    tenant_id: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    scopes: List[str] = field(default_factory=list)
    is_authenticated: bool = False
    token_payload: dict[str, Any] = field(default_factory=dict)

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def has_any_role(self, *roles: str) -> bool:
        return any(r in self.roles for r in roles)

    def has_all_roles(self, *roles: str) -> bool:
        return all(r in self.roles for r in roles)


ANONYMOUS_PRINCIPAL = Principal(id="", is_authenticated=False)

bearer_scheme = HTTPBearer(auto_error=False)


class BearerTokenAuth(HTTPBearer):
    def __init__(self, auto_error: bool = False) -> None:
        super().__init__(auto_error=auto_error)


class CookieAuth:
    def __init__(self, cookie_name: str = "access_token") -> None:
        self.cookie_name = cookie_name

    async def __call__(self, request: Request) -> Optional[str]:
        token = request.cookies.get(self.cookie_name)
        return token


async def get_token_from_header(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[str]:
    if credentials:
        return credentials.credentials
    return None


async def get_token_from_cookie(
    request: Request,
    cookie_name: str = "access_token",
) -> Optional[str]:
    return request.cookies.get(cookie_name)


async def resolve_principal(
    token: Optional[str] = Depends(get_token_from_header),
) -> Principal:
    if not token:
        return ANONYMOUS_PRINCIPAL
    try:
        payload = decode_token(token)
        principal = Principal(
            id=payload.get("sub", ""),
            tenant_id=payload.get("tenant_id"),
            roles=payload.get("roles", []),
            scopes=payload.get("scopes", []),
            is_authenticated=True,
            token_payload=payload,
        )
        return principal
    except ValueError as e:
        logger.warning("Token resolution failed: %s", e)
        return ANONYMOUS_PRINCIPAL
    except Exception as e:
        logger.error("Unexpected token resolution error: %s", e)
        return ANONYMOUS_PRINCIPAL


async def get_principal(
    principal: Principal = Depends(resolve_principal),
) -> Principal:
    return principal


def require_roles(*roles: str) -> Callable[[Principal], Awaitable[Principal]]:
    async def _require_roles(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        if not principal.has_any_role(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient roles. Required one of: {', '.join(roles)}",
            )
        return principal

    return _require_roles


def require_scopes(*scopes: str) -> Callable[[Principal], Awaitable[Principal]]:
    async def _require_scopes(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        for scope in scopes:
            if not principal.has_scope(scope):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required scope: {scope}",
                )
        return principal

    return _require_scopes


async def require_active_user(
    principal: Principal = Depends(get_principal),
) -> Principal:
    if not principal.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return principal


def require_tenant_membership(
    tenant_id: str,
) -> Callable[[Principal], Awaitable[Principal]]:
    async def _require_tenant(
        principal: Principal = Depends(get_principal),
    ) -> Principal:
        if not principal.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        if principal.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this tenant",
            )
        return principal

    return _require_tenant
