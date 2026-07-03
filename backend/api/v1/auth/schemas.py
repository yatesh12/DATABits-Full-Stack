from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=150, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = Field(None, max_length=255)
    tenant_slug: str | None = Field(None, max_length=255)


class RegisterResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: str | None
    created_at: datetime


class LoginRequest(BaseModel):
    username: str | None = Field(None, max_length=150)
    email: EmailStr | None = None
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str


class SessionResponse(BaseModel):
    id: int
    ip_address: str | None
    user_agent: str | None
    device_info: dict[str, Any] | None
    created_at: datetime
    expires_at: datetime
    is_revoked: bool
    is_current: bool = False


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
    avatar_url: str | None
    display_name: str | None
    tenant_id: str | None
    created_at: datetime | None
    updated_at: datetime | None
    last_login: datetime | None


class LogoutResponse(BaseModel):
    message: str = "Logged out successfully"


class MessageResponse(BaseModel):
    message: str
