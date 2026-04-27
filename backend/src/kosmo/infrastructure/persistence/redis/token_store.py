from redis.asyncio import Redis

_REFRESH_PREFIX = "auth:refresh:"
_REVOKED_PREFIX = "auth:revoked:"


class RedisTokenRevocationStore:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def register_refresh(self, *, jti: str, subject: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        await self._client.set(_REFRESH_PREFIX + jti, subject, ex=ttl_seconds)

    async def consume_refresh(self, *, jti: str) -> str | None:
        key = _REFRESH_PREFIX + jti
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.get(key)
            pipe.delete(key)
            stored, _ = await pipe.execute()
        if stored is None:
            return None
        return stored.decode("utf-8") if isinstance(stored, bytes) else str(stored)

    async def revoke_access(self, *, jti: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        await self._client.set(_REVOKED_PREFIX + jti, "1", ex=ttl_seconds)

    async def is_access_revoked(self, *, jti: str) -> bool:
        return bool(await self._client.exists(_REVOKED_PREFIX + jti))

    async def revoke_refresh(self, *, jti: str) -> None:
        await self._client.delete(_REFRESH_PREFIX + jti)
