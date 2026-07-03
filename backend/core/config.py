from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App Info ──────────────────────────────────────────────────────────
    PROJECT_NAME: str = Field("DATABits", alias="PROJECT_NAME")
    VERSION: str = Field("1.0.0", alias="VERSION")
    DEBUG: bool = Field(False, alias="DEBUG")
    ENVIRONMENT: str = Field("development", alias="ENVIRONMENT")
    API_V1_PREFIX: str = Field("/api/v1", alias="API_V1_PREFIX")

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/databits",
        alias="DATABASE_URL",
    )
    DATABASE_SYNC_URL: str = Field(
        "postgresql://postgres:postgres@localhost:5432/databits",
        alias="DATABASE_SYNC_URL",
    )
    DATABASE_POOL_SIZE: int = Field(20, alias="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(10, alias="DATABASE_MAX_OVERFLOW")
    DATABASE_POOL_TIMEOUT: int = Field(30, alias="DATABASE_POOL_TIMEOUT")
    DATABASE_ECHO: bool = Field(False, alias="DATABASE_ECHO")
    DATABASE_POOL_PRE_PING: bool = Field(True, alias="DATABASE_POOL_PRE_PING")

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    REDIS_POOL_SIZE: int = Field(20, alias="REDIS_POOL_SIZE")
    REDIS_POOL_TIMEOUT: int = Field(5, alias="REDIS_POOL_TIMEOUT")
    REDIS_SOCKET_TIMEOUT: int = Field(5, alias="REDIS_SOCKET_TIMEOUT")
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(5, alias="REDIS_SOCKET_CONNECT_TIMEOUT")
    REDIS_RETRY_ON_TIMEOUT: bool = Field(True, alias="REDIS_RETRY_ON_TIMEOUT")
    REDIS_HEALTH_CHECK_INTERVAL: int = Field(30, alias="REDIS_HEALTH_CHECK_INTERVAL")

    # ── JWT ───────────────────────────────────────────────────────────────
    JWT_SECRET: str = Field("change-me-secret-key", alias="JWT_SECRET")
    JWT_ALGORITHM: str = Field("RS256", alias="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    JWT_ISSUER: str = Field("databits", alias="JWT_ISSUER")
    JWT_AUDIENCE: str = Field("databits-api", alias="JWT_AUDIENCE")

    # ── RSA Keys ──────────────────────────────────────────────────────────
    RSA_PRIVATE_KEY_PATH: Optional[str] = Field(None, alias="RSA_PRIVATE_KEY_PATH")
    RSA_PUBLIC_KEY_PATH: Optional[str] = Field(None, alias="RSA_PUBLIC_KEY_PATH")

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        alias="CORS_ORIGINS",
    )
    CORS_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        alias="CORS_METHODS",
    )
    CORS_HEADERS: List[str] = Field(
        default=["*"],
        alias="CORS_HEADERS",
    )
    TRUSTED_HOSTS: List[str] = Field(
        default=["*"],
        alias="TRUSTED_HOSTS",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    # ── File Upload ───────────────────────────────────────────────────────
    FILE_UPLOAD_MAX_SIZE: int = Field(100 * 1024 * 1024, alias="FILE_UPLOAD_MAX_SIZE")  # 100 MB
    FILE_UPLOAD_ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".csv", ".xlsx", ".xls", ".json", ".parquet", ".tsv", ".xml"],
        alias="FILE_UPLOAD_ALLOWED_EXTENSIONS",
    )
    FILE_UPLOAD_DIR: str = Field("uploads", alias="FILE_UPLOAD_DIR")

    # ── S3 / Tigris ───────────────────────────────────────────────────────
    S3_ENDPOINT: Optional[str] = Field(None, alias="S3_ENDPOINT")
    S3_ACCESS_KEY_ID: Optional[str] = Field(None, alias="S3_ACCESS_KEY_ID")
    S3_SECRET_ACCESS_KEY: Optional[str] = Field(None, alias="S3_SECRET_ACCESS_KEY")
    S3_BUCKET_NAME: str = Field("databits", alias="S3_BUCKET_NAME")
    S3_REGION: str = Field("us-east-1", alias="S3_REGION")
    S3_USE_SSL: bool = Field(True, alias="S3_USE_SSL")

    # ── Celery ────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = Field("redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field("redis://localhost:6379/1", alias="CELERY_RESULT_BACKEND")
    CELERY_TASK_SERIALIZER: str = Field("json", alias="CELERY_TASK_SERIALIZER")
    CELERY_RESULT_SERIALIZER: str = Field("json", alias="CELERY_RESULT_SERIALIZER")
    CELERY_ACCEPT_CONTENT: List[str] = Field(
        default=["json"],
        alias="CELERY_ACCEPT_CONTENT",
    )
    CELERY_TASK_TRACK_STARTED: bool = Field(True, alias="CELERY_TASK_TRACK_STARTED")
    CELERY_TASK_TIME_LIMIT: int = Field(3600, alias="CELERY_TASK_TIME_LIMIT")
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(3000, alias="CELERY_TASK_SOFT_TIME_LIMIT")
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP: bool = Field(
        True, alias="CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP"
    )

    # ── Sentry ────────────────────────────────────────────────────────────
    SENTRY_DSN: Optional[str] = Field(None, alias="SENTRY_DSN")
    SENTRY_TRACES_SAMPLE_RATE: float = Field(0.1, alias="SENTRY_TRACES_SAMPLE_RATE")

    # ── Logging ───────────────────────────────────────────────────────────
    LOG_LEVEL: str = Field("INFO", alias="LOG_LEVEL")
    LOG_FORMAT: str = Field("json", alias="LOG_FORMAT")  # "json" | "console"
    LOG_JSON: bool = Field(True, alias="LOG_JSON")

    # ── Rate Limiting ─────────────────────────────────────────────────────
    RATE_LIMIT_WINDOW_SECONDS: int = Field(60, alias="RATE_LIMIT_WINDOW_SECONDS")
    RATE_LIMIT_MAX_REQUESTS: int = Field(100, alias="RATE_LIMIT_MAX_REQUESTS")

    # ── Email (SMTP) ──────────────────────────────────────────────────────
    SMTP_HOST: Optional[str] = Field(None, alias="SMTP_HOST")
    SMTP_PORT: int = Field(587, alias="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(None, alias="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(None, alias="SMTP_PASSWORD")
    SMTP_FROM_EMAIL: Optional[str] = Field(None, alias="SMTP_FROM_EMAIL")
    SMTP_FROM_NAME: str = Field("DATABits", alias="SMTP_FROM_NAME")
    SMTP_USE_TLS: bool = Field(True, alias="SMTP_USE_TLS")

    # ── Stripe ────────────────────────────────────────────────────────────
    STRIPE_API_KEY: Optional[str] = Field(None, alias="STRIPE_API_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(None, alias="STRIPE_WEBHOOK_SECRET")
    STRIPE_STARTER_PRICE_ID: Optional[str] = Field(None, alias="STRIPE_STARTER_PRICE_ID")
    STRIPE_PRO_PRICE_ID: Optional[str] = Field(None, alias="STRIPE_PRO_PRICE_ID")
    STRIPE_ENTERPRISE_PRICE_ID: Optional[str] = Field(None, alias="STRIPE_ENTERPRISE_PRICE_ID")

    # ── Razorpay ──────────────────────────────────────────────────────────
    RAZORPAY_KEY_ID: Optional[str] = Field(None, alias="RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET: Optional[str] = Field(None, alias="RAZORPAY_KEY_SECRET")
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = Field(None, alias="RAZORPAY_WEBHOOK_SECRET")

    # ── Groq ──────────────────────────────────────────────────────────────
    GROQ_API_KEY: Optional[str] = Field(None, alias="GROQ_API_KEY")
    GROQ_MODEL: str = Field("mixtral-8x7b-32768", alias="GROQ_MODEL")

    # ── Qdrant ────────────────────────────────────────────────────────────
    QDRANT_URL: Optional[str] = Field(None, alias="QDRANT_URL")
    QDRANT_API_KEY: Optional[str] = Field(None, alias="QDRANT_API_KEY")
    QDRANT_COLLECTION_NAME: str = Field("databits", alias="QDRANT_COLLECTION_NAME")

    # ── Usage Limits ──────────────────────────────────────────────────────
    USAGE_MAX_DATASETS_DEFAULT: int = Field(10, alias="USAGE_MAX_DATASETS_DEFAULT")
    USAGE_MAX_FILE_SIZE_MB: int = Field(100, alias="USAGE_MAX_FILE_SIZE_MB")
    USAGE_MAX_ROWS_DEFAULT: int = Field(100_000, alias="USAGE_MAX_ROWS_DEFAULT")

    # ── Feature Flags ─────────────────────────────────────────────────────
    FEATURE_SIGNUP_ENABLED: bool = Field(True, alias="FEATURE_SIGNUP_ENABLED")
    FEATURE_FILE_UPLOAD: bool = Field(True, alias="FEATURE_FILE_UPLOAD")
    FEATURE_BILLING: bool = Field(False, alias="FEATURE_BILLING")
    FEATURE_ASSISTANT: bool = Field(True, alias="FEATURE_ASSISTANT")
    FEATURE_COMMUNITY: bool = Field(True, alias="FEATURE_COMMUNITY")
    FEATURE_WEBHOOKS: bool = Field(False, alias="FEATURE_WEBHOOKS")
    FEATURE_TEAMS: bool = Field(True, alias="FEATURE_TEAMS")

    @property
    def IS_PRODUCTION(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def IS_DEVELOPMENT(self) -> bool:
        return self.ENVIRONMENT.lower() in ("development", "dev")

    @property
    def RSA_PRIVATE_KEY(self) -> Optional[str]:
        if self.RSA_PRIVATE_KEY_PATH:
            path = Path(self.RSA_PRIVATE_KEY_PATH)
            if path.exists():
                return path.read_text()
        return None

    @property
    def RSA_PUBLIC_KEY(self) -> Optional[str]:
        if self.RSA_PUBLIC_KEY_PATH:
            path = Path(self.RSA_PUBLIC_KEY_PATH)
            if path.exists():
                return path.read_text()
        return None

    def dict_without_sensitive(self) -> dict[str, Any]:
        sensitive_keys = {
            "JWT_SECRET", "RSA_PRIVATE_KEY_PATH", "RSA_PUBLIC_KEY_PATH",
            "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY",
            "SMTP_PASSWORD", "STRIPE_API_KEY", "STRIPE_WEBHOOK_SECRET",
            "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET",
            "GROQ_API_KEY", "QDRANT_API_KEY",
        }
        return {
            k: ("***" if k in sensitive_keys and v else v)
            for k, v in self.model_dump().items()
        }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
