from typing import Any, cast

from fastapi import HTTPException, Request, status

from kosmo.infrastructure.api.dependencies.container import get_container


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
        redis = cast(Any, get_container(request).redis)
        if redis is None:
            return
        client_ip = request.client.host if request.client else "unknown"
        key = f"auth:ip_rate:{request.url.path}:{client_ip}"
        count = int(await redis.eval(self._LUA_SCRIPT, 1, key, str(self._limit), "60"))
        if count > self._limit:
            ttl = int(await redis.ttl(key))
            retry_after = max(ttl, 1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Demasiadas solicitudes. Intente de nuevo en {retry_after} segundos.",
                headers={"Retry-After": str(retry_after)},
            )


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
        redis = cast(Any, get_container(request).redis)
        if redis is None:
            return
        key = f"gen:rate:{project_id}"
        count = int(await redis.eval(self._LUA_SCRIPT, 1, key, str(self._limit), "3600"))
        if count > self._limit:
            ttl = int(await redis.ttl(key))
            retry_after = max(ttl, 1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Limite de generaciones excedido para el proyecto. Intente de nuevo en {retry_after} segundos.",
                headers={"Retry-After": str(retry_after)},
            )
