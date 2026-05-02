from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_logger = structlog.get_logger("kosmo.http")
_tracer = trace.get_tracer("kosmo.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)

        method = request.method
        path = request.url.path

        try:
            with _tracer.start_as_current_span(
                "http.request",
                attributes={
                    "http.method": method,
                    "http.url": str(request.url),
                    "http.route": path,
                },
            ) as span:
                start = time.perf_counter()
                try:
                    response = await call_next(request)
                except Exception as exc:
                    duration_ms = (time.perf_counter() - start) * 1000
                    span.record_exception(exc)
                    span.set_status(trace.StatusCode.ERROR, str(exc))
                    _logger.error(
                        "http.request.failed",
                        method=method,
                        path=path,
                        duration_ms=round(duration_ms, 3),
                        request_id=request_id,
                        exc_info=True,
                    )
                    raise

                duration_ms = (time.perf_counter() - start) * 1000
                span.set_attribute("http.status_code", response.status_code)
                route = request.scope.get("route")
                if route is not None:
                    span.set_attribute("http.route", getattr(route, "path", path))

                _logger.info(
                    "http.request.completed",
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 3),
                    request_id=request_id,
                )
            return response
        finally:
            structlog.contextvars.clear_contextvars()
