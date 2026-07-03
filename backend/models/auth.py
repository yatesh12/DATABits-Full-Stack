import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base

try:
    from passlib.context import CryptContext

    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    _pwd_context = None


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", type_=JSON, nullable=True
    )

    tenant: Mapped["TenantModel"] = relationship(
        "TenantModel", back_populates="users", lazy="selectin"
    )
    sessions: Mapped[list["SessionModel"]] = relationship(
        "SessionModel", back_populates="user", lazy="selectin",
        cascade="all, delete-orphan"
    )
    identities: Mapped[list["IdentityModel"]] = relationship(
        "IdentityModel", back_populates="user", lazy="selectin",
        cascade="all, delete-orphan"
    )
    password_resets: Mapped[list["PasswordResetModel"]] = relationship(
        "PasswordResetModel", back_populates="user", lazy="selectin",
        cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        if _pwd_context is None:
            raise RuntimeError("passlib is not installed")
        self.hashed_password = _pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        if _pwd_context is None:
            raise RuntimeError("passlib is not installed")
        return _pwd_context.verify(password, self.hashed_password)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "is_superuser": self.is_superuser,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "avatar_url": self.avatar_url,
            "display_name": self.display_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "metadata": self.metadata,
        }


class TenantModel(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    plan: Mapped[str | None] = mapped_column(String(50), nullable=True, default="free")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    settings: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_datasets: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    storage_limit_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1073741824
    )

    users: Mapped[list["UserModel"]] = relationship(
        "UserModel", back_populates="tenant", lazy="selectin"
    )
    datasets: Mapped[list["DatasetModel"]] = relationship(
        "DatasetModel", back_populates="tenant", lazy="selectin"
    )
    subscriptions: Mapped[list["SubscriptionModel"]] = relationship(
        "SubscriptionModel", back_populates="tenant", lazy="selectin"
    )
    usage: Mapped[list["UsageModel"]] = relationship(
        "UsageModel", back_populates="tenant", lazy="selectin"
    )
    transactions: Mapped[list["TransactionModel"]] = relationship(
        "TransactionModel", back_populates="tenant", lazy="selectin"
    )


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    device_info: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="sessions", lazy="selectin"
    )


class IdentityModel(Base):
    __tablename__ = "identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    provider_id: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    provider_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="identities", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="uq_identity_provider"),
    )


class PasswordResetModel(Base):
    __tablename__ = "password_resets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="password_resets", lazy="selectin"
    )
