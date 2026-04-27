from typing import Protocol

from kosmo.contracts.auth.tokens import IssuedToken, TokenClaims, TokenType


class TokenIssuer(Protocol):
    def issue(
        self,
        *,
        subject: str,
        scopes: frozenset[str],
        token_type: TokenType,
    ) -> IssuedToken: ...


class TokenVerifier(Protocol):
    def verify(self, token: str, *, expected_type: TokenType) -> TokenClaims: ...


class TokenRevocationStore(Protocol):
    async def register_refresh(self, *, jti: str, subject: str, ttl_seconds: int) -> None: ...

    async def consume_refresh(self, *, jti: str) -> str | None: ...

    async def revoke_access(self, *, jti: str, ttl_seconds: int) -> None: ...

    async def is_access_revoked(self, *, jti: str) -> bool: ...

    async def revoke_refresh(self, *, jti: str) -> None: ...
