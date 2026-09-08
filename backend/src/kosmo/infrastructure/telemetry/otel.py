from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from opentelemetry import metrics, trace

from kosmo.contracts.telemetry import TelemetryPort


class OpenTelemetryProvider(TelemetryPort):
    """Adaptador de infraestructura para telemetría usando OpenTelemetry."""

    def __init__(self, tracer_name: str = "kosmo.business", meter_name: str = "kosmo.auth") -> None:
        self._tracer = trace.get_tracer(tracer_name)
        self._meter = metrics.get_meter(meter_name)
        self._auth_events = self._meter.create_counter(
            "kosmo.auth.events",
            unit="1",
            description="Authentication events by type",
        )

    def trace_sync(
        self,
        span_name: str,
        attributes: dict[str, Any],
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        with self._tracer.start_as_current_span(span_name, attributes=attributes) as span:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(trace.StatusCode.ERROR, str(exc))
                raise

    async def trace_async(
        self,
        span_name: str,
        attributes: dict[str, Any],
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        with self._tracer.start_as_current_span(span_name, attributes=attributes) as span:
            try:
                res = func(*args, **kwargs)
                if inspect.isawaitable(res):
                    return await res
                return res
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(trace.StatusCode.ERROR, str(exc))
                raise

    def record_auth_event(self, event_type: str, user_id: str | None = None) -> None:
        attributes: dict[str, str] = {"event_type": event_type}
        if user_id is not None:
            attributes["user_id"] = user_id
        self._auth_events.add(1, attributes)
