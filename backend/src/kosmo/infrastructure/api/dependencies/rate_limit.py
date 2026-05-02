from fastapi import HTTPException, Request, status


class IpRateLimiter:
    def __init__(self, requests_per_minute: int) -> None:
        self._limit = requests_per_minute

    async def __call__(self, request: Request) -> None:
        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return
        client_ip = request.client.host if request.client else "unknown"
        key = f"auth:ip_rate:{request.url.path}:{client_ip}"
        count = int(await redis.incr(key))
        if count == 1:
            await redis.expire(key, 60)
        if count > self._limit:
            ttl = int(await redis.ttl(key))
            retry_after = max(ttl, 1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Demasiadas solicitudes. Intente de nuevo en {retry_after} segundos.",
                headers={"Retry-After": str(retry_after)},
            )
