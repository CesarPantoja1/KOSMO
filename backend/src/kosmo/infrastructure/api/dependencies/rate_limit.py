from __future__ import annotations

from typing import Any, cast

import structlog
from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from kosmo.infrastructure.api.dependencies.container import get_container

_log = structlog.get_logger("kosmo.rate_limit")


def _should_fail_closed(container: Any) -> bool:
    settings = getattr(container, "settings", None)
    if settings is None:
        return False
    return bool(
        getattr(settings, "rate_limit_required", False) or getattr(settings, "env", "") in ("production", "staging")
    )


class IpRateLimiter:
    _LUA_SCRIPT = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local current = redis.call('INCR', key)
        if current == 1 then
            redis.call('EXPIRE', key, window)
        end
        return current
    """

    def __init__(self, requests_per_minute: int) -> None:
        self._limit = requests_per_minute

    async def __call__(self, request: Request) -> None:
        container = get_container(request)
        redis = cast(Any, getattr(container, "redis", None))
        fail_closed = _should_fail_closed(container)

        if redis is None:
            if fail_closed:
                _log.error("rate_limit.redis_unavailable_fail_closed", path=request.url.path)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Servicio de limitación de tasa no disponible.",
                )
            _log.warning("rate_limit.bypassed_no_redis", path=request.url.path)
            return

        # Public deployments pass the original Cloudflare client address through
        # Nginx in this header. The backend itself is only reachable on the
        # private Compose network; direct/local calls retain their socket IP.
        client_ip = request.headers.get("x-kosmo-client-ip") or (request.client.host if request.client else "unknown")
        key = f"auth:ip_rate:{request.url.path}:{client_ip}"
        try:
            count = int(await redis.eval(self._LUA_SCRIPT, 1, key, str(self._limit), "60"))
            if count > self._limit:
                ttl = int(await redis.ttl(key))
                retry_after = max(ttl, 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Demasiadas solicitudes. Intente de nuevo en {retry_after} segundos.",
                    headers={"Retry-After": str(retry_after)},
                )
        except HTTPException:
            raise
        except (RedisError, ConnectionError, TimeoutError, OSError) as exc:
            if fail_closed:
                _log.error("rate_limit.redis_eval_failed_fail_closed", path=request.url.path, error=str(exc))
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Servicio de limitación de tasa temporalmente no disponible.",
                ) from exc
            _log.warning("rate_limit.redis_eval_failed_bypassed", path=request.url.path, error=str(exc))
            return


class ProjectGenerationRateLimiter:
    _LUA_SCRIPT = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local current = redis.call('INCR', key)
        if current == 1 then
            redis.call('EXPIRE', key, window)
        end
        return current
    """

    def __init__(self, requests_per_hour: int) -> None:
        self._limit = requests_per_hour

    async def __call__(self, request: Request, project_id: str = "") -> None:
        if not project_id:
            project_id = request.path_params.get("project_id", "unknown")
        container = get_container(request)
        redis = cast(Any, getattr(container, "redis", None))
        fail_closed = _should_fail_closed(container)

        if redis is None:
            if fail_closed:
                _log.error("rate_limit.redis_unavailable_fail_closed", project_id=project_id)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Servicio de limitación de tasa no disponible.",
                )
            _log.warning("rate_limit.bypassed_no_redis", project_id=project_id)
            return

        key = f"gen:rate:{project_id}"
        try:
            count = int(await redis.eval(self._LUA_SCRIPT, 1, key, str(self._limit), "3600"))
            if count > self._limit:
                ttl = int(await redis.ttl(key))
                retry_after = max(ttl, 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Limite de generaciones excedido para el proyecto. Intente de nuevo en {retry_after} segundos."
                    ),
                    headers={"Retry-After": str(retry_after)},
                )
        except HTTPException:
            raise
        except (RedisError, ConnectionError, TimeoutError, OSError) as exc:
            if fail_closed:
                _log.error("rate_limit.redis_eval_failed_fail_closed", project_id=project_id, error=str(exc))
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Servicio de limitación de tasa temporalmente no disponible.",
                ) from exc
            _log.warning("rate_limit.redis_eval_failed_bypassed", project_id=project_id, error=str(exc))
            return
