from __future__ import annotations

from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    status_code: int = 500
    detail: str = "Internal server error"
    error_code: str = "internal_error"
    headers: Optional[dict[str, str]] = None

    def __init__(
        self,
        detail: Optional[str] = None,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> None:
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.headers = headers
        self.extra = extra or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.error_code,
            "detail": self.detail,
            "status_code": self.status_code,
            **self.extra,
        }


class NotFoundException(AppException):
    status_code: int = 404
    detail: str = "Resource not found"
    error_code: str = "not_found"


class ValidationException(AppException):
    status_code: int = 400
    detail: str = "Validation error"
    error_code: str = "validation_error"


class AuthException(AppException):
    status_code: int = 401
    detail: str = "Authentication failed"
    error_code: str = "auth_error"
    headers: Optional[dict[str, str]] = {"WWW-Authenticate": "Bearer"}


class ForbiddenException(AppException):
    status_code: int = 403
    detail: str = "Access forbidden"
    error_code: str = "forbidden"


class ConflictException(AppException):
    status_code: int = 409
    detail: str = "Resource conflict"
    error_code: str = "conflict"


class RateLimitException(AppException):
    status_code: int = 429
    detail: str = "Rate limit exceeded"
    error_code: str = "rate_limit_exceeded"


class PaymentRequiredException(AppException):
    status_code: int = 402
    detail: str = "Payment required"
    error_code: str = "payment_required"


class ServiceUnavailableException(AppException):
    status_code: int = 503
    detail: str = "Service temporarily unavailable"
    error_code: str = "service_unavailable"


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
        headers=exc.headers,
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "detail": "An unexpected error occurred",
            "status_code": 500,
        },
    )


async def validation_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    from fastapi.exceptions import RequestValidationError

    if isinstance(exc, RequestValidationError):
        errors = exc.errors()
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "detail": "Request validation failed",
                "errors": errors,
                "status_code": 422,
            },
        )
    return JSONResponse(
        status_code=400,
        content={
            "error": "validation_error",
            "detail": str(exc),
            "status_code": 400,
        },
    )


def register_exception_handlers(app: Any) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(NotFoundException, app_exception_handler)
    app.add_exception_handler(ValidationException, app_exception_handler)
    app.add_exception_handler(AuthException, app_exception_handler)
    app.add_exception_handler(ForbiddenException, app_exception_handler)
    app.add_exception_handler(ConflictException, app_exception_handler)
    app.add_exception_handler(RateLimitException, app_exception_handler)
    app.add_exception_handler(PaymentRequiredException, app_exception_handler)

    from fastapi.exceptions import RequestValidationError

    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)
