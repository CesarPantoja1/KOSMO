from __future__ import annotations

import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, cast

from opentelemetry import metrics, trace

P = ParamSpec("P")
R = TypeVar("R")

_tracer = trace.get_tracer("kosmo.business")
_meter = metrics.get_meter("kosmo.auth")

_auth_events = _meter.create_counter(
    "kosmo.auth.events",
    unit="1",
    description="Authentication events by type",
)


def traced(
    span_name: str, attributes: dict[str, Any] | None = None
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    span_attrs: dict[str, Any] = dict(attributes) if attributes else {}

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                with _tracer.start_as_current_span(span_name, attributes=span_attrs) as span:
                    try:
                        return await cast(Callable[P, Awaitable[R]], func)(*args, **kwargs)
                    except Exception as exc:
                        span.record_exception(exc)
                        span.set_status(trace.StatusCode.ERROR, str(exc))
                        raise

            return cast(Callable[P, R], async_wrapper)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with _tracer.start_as_current_span(span_name, attributes=span_attrs) as span:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(trace.StatusCode.ERROR, str(exc))
                    raise

        return sync_wrapper

    return decorator


def record_auth_event(event_type: str, user_id: str | None = None) -> None:
    attributes: dict[str, str] = {"event_type": event_type}
    if user_id is not None:
        attributes["user_id"] = user_id
    _auth_events.add(1, attributes)
