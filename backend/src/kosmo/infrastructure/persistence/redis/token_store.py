from redis.asyncio import Redis

from kosmo.contracts.auth import RefreshConsumeResult

_REFRESH_PREFIX = "auth:refresh:"
_REVOKED_ACCESS_PREFIX = "auth:revoked:access:"
_FAMILY_PREFIX = "auth:family:"
_FAMILY_SEPARATOR = "|"


class RedisTokenRevocationStore:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def register_refresh(
        self,
        *,
        jti: str,
        subject: str,
        ttl_seconds: int,
        family_id: str | None = None,
    ) -> None:
        if ttl_seconds <= 0:
            return
        value = subject if family_id is None else f"{subject}{_FAMILY_SEPARATOR}{family_id}"
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.set(_REFRESH_PREFIX + jti, value, ex=ttl_seconds)
            if family_id is not None:
                pipe.set(_FAMILY_PREFIX + family_id, subject, ex=ttl_seconds)
            await pipe.execute()

    async def consume_refresh(self, *, jti: str) -> RefreshConsumeResult | None:
        key = _REFRESH_PREFIX + jti
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.get(key)
            pipe.delete(key)
            stored, _ = await pipe.execute()
        if stored is None:
            return None
        raw = stored.decode("utf-8") if isinstance(stored, bytes) else str(stored)
        if _FAMILY_SEPARATOR in raw:
            subject, family_id = raw.split(_FAMILY_SEPARATOR, 1)
            return RefreshConsumeResult(subject=subject, family_id=family_id)
        return RefreshConsumeResult(subject=raw, family_id=None)

    async def revoke_access(self, *, jti: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        await self._client.set(_REVOKED_ACCESS_PREFIX + jti, "1", ex=ttl_seconds)

    async def is_access_revoked(self, *, jti: str) -> bool:
        return bool(await self._client.exists(_REVOKED_ACCESS_PREFIX + jti))

    async def revoke_refresh(self, *, jti: str) -> None:
        await self._client.delete(_REFRESH_PREFIX + jti)

    async def is_family_alive(self, *, family_id: str) -> bool:
        return bool(await self._client.exists(_FAMILY_PREFIX + family_id))

    async def revoke_family(self, *, family_id: str) -> None:
        await self._client.delete(_FAMILY_PREFIX + family_id)
