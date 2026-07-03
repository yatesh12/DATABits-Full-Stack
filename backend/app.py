import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.structlog import StructlogIntegration
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from api.v1.router import api_router
from core.config import get_settings
from core.logging import setup_structlog

settings = get_settings()


def setup_sentry() -> None:
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            integrations=[
                StarletteIntegration(),
                FastApiIntegration(),
                StructlogIntegration(),
            ],
        )


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call):
        import time as t_mod

        start = t_mod.time()
        response = await call(request)
        duration = t_mod.time() - start
        # Push to Prometheus metrics in production
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_sentry()
    setup_structlog()
    logger = structlog.get_logger(__name__)
    logger.info("Application startup", environment=settings.ENVIRONMENT)
    yield
    logger.info("Application shutdown")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.TRUSTED_HOSTS if settings.TRUSTED_HOSTS else ["*"],
)


app.add_middleware(GZipMiddleware, minimum_size=1000)


app.add_middleware(PrometheusMiddleware)


metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger = structlog.get_logger(__name__)
    logger.exception(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    logger = structlog.get_logger(__name__)
    logger.warning(
        "Validation error",
        path=request.url.path,
        error=str(exc),
    )
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
