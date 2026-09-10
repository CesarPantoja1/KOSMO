from __future__ import annotations

import ipaddress
from typing import Any, cast

import structlog
from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from kosmo.infrastructure.api.dependencies.container import get_container

_log = structlog.get_logger("kosmo.rate_limit")
_DEFAULT_TRUSTED_PROXIES = "127.0.0.1,::1,testclient,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"


def _should_fail_closed(container: Any) -> bool:
    settings = getattr(container, "settings", None)
    if settings is None:
        return False
    return bool(
        getattr(settings, "rate_limit_required", False) or getattr(settings, "env", "") in ("production", "staging")
    )


def _is_trusted_proxy(host: str, trusted_proxies_cfg: str) -> bool:
    if not host:
        return False
    proxies = [p.strip() for p in trusted_proxies_cfg.split(",") if p.strip()]
    if host in proxies:
        return True
    try:
        host_ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    for proxy in proxies:
        try:
            if "/" in proxy:
                if host_ip in ipaddress.ip_network(proxy, strict=False):
                    return True
            elif host_ip == ipaddress.ip_address(proxy):
                return True
        except ValueError:
            continue
    return False


def _resolve_client_ip(request: Request, container: Any) -> str:
    host = request.client.host if request.client else ""
    if not host:
        return "unknown"

    settings = getattr(container, "settings", None)
    trusted_proxies = getattr(settings, "trusted_proxies", _DEFAULT_TRUSTED_PROXIES)
    if _is_trusted_proxy(host, trusted_proxies):
        header_ip = (request.headers.get("x-kosmo-client-ip") or "").strip()
        if header_ip:
            try:
                ipaddress.ip_address(header_ip)
                return header_ip
            except ValueError:
                pass
    return host


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

        # Public deployments pass the client address through a trusted reverse proxy
        # in x-kosmo-client-ip. Header is only trusted if the connection originates
        # from a verified trusted proxy address or subnet.
        client_ip = _resolve_client_ip(request, container)
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
