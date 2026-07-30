from __future__ import annotations

import time

import structlog
from opentelemetry import trace
from ulid import ULID

_logger = structlog.get_logger("kosmo.http")
_tracer = trace.get_tracer("kosmo.http")


class RequestLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = ULID().hex
        client = scope.get("client")
        ip_address = client[0] if client is not None else None
        headers = dict(scope.get("headers", []))
        user_agent = headers.get(b"user-agent", b"").decode("utf-8", errors="replace")

        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        method = scope["method"]
        path = scope["path"]

        start = time.perf_counter()
        status_code = [None]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message["status"]
            await send(message)

        try:
            with _tracer.start_as_current_span(
                "http.request",
                attributes={
                    "http.method": method,
                    "http.url": scope.get("root_path", "") + path,
                    "http.route": path,
                },
            ) as span:
                try:
                    await self.app(scope, receive, send_wrapper)
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
                code = status_code[0]
                if code is not None:
                    span.set_attribute("http.status_code", code)

                _logger.info(
                    "http.request.completed",
                    method=method,
                    path=path,
                    status_code=code,
                    duration_ms=round(duration_ms, 3),
                    request_id=request_id,
                )
        finally:
            structlog.contextvars.clear_contextvars()
