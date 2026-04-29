import json
from datetime import UTC, datetime

from redis.asyncio import Redis

from kosmo.contracts.auth import AuthorizationCode, PkceMethod

_AUTHCODE_PREFIX = "auth:authcode:"


class RedisAuthorizationCodeStore:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def store(self, entry: AuthorizationCode) -> None:
        ttl = max(int((entry.expires_at - datetime.now(UTC)).total_seconds()), 1)
        payload = {
            "subject": entry.subject,
            "code_challenge": entry.code_challenge,
            "code_challenge_method": entry.code_challenge_method.value,
            "expires_at": entry.expires_at.isoformat(),
            "scopes": sorted(entry.scopes),
        }
        await self._client.set(
            _AUTHCODE_PREFIX + entry.code,
            json.dumps(payload),
            ex=ttl,
            nx=True,
        )

    async def consume(self, code: str) -> AuthorizationCode | None:
        key = _AUTHCODE_PREFIX + code
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.get(key)
            pipe.delete(key)
            stored, _ = await pipe.execute()
        if stored is None:
            return None
        raw = stored.decode("utf-8") if isinstance(stored, bytes) else str(stored)
        data = json.loads(raw)
        return AuthorizationCode(
            code=code,
            subject=str(data["subject"]),
            code_challenge=str(data["code_challenge"]),
            code_challenge_method=PkceMethod(data["code_challenge_method"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            scopes=frozenset(data.get("scopes") or []),
        )
