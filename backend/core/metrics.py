from __future__ import annotations

import time
from typing import Callable

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, Request, Response
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.routing import Match

request_count = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["endpoint", "method", "status"],
)

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["endpoint", "method"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

request_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently in progress",
    labelnames=["method"],
)

error_counter = Counter(
    "app_errors_total",
    "Total application errors by type",
    labelnames=["error_type", "endpoint"],
)

active_connections = Gauge(
    "app_active_connections",
    "Number of active connections",
    labelnames=["type"],
)


def _get_route_path(request: StarletteRequest) -> str:
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return route.path
    return request.url.path


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: StarletteRequest,
        call_next: Callable[[StarletteRequest], StarletteResponse],
    ) -> StarletteResponse:
        method = request.method
        path = _get_route_path(request)

        request_in_progress.labels(method=method).inc()

        start = time.perf_counter()
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as exc:
            status = 500
            error_counter.labels(
                error_type=type(exc).__name__,
                endpoint=path,
            ).inc()
            raise
        finally:
            duration = time.perf_counter() - start
            request_duration.labels(endpoint=path, method=method).observe(duration)
            request_count.labels(endpoint=path, method=method, status=str(status)).inc()
            request_in_progress.labels(method=method).dec()

        return response


async def metrics_endpoint(request: StarletteRequest) -> StarletteResponse:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    data = generate_latest()
    return StarletteResponse(
        content=data,
        media_type=CONTENT_TYPE_LATEST,
    )
