from dataclasses import dataclass
from datetime import UTC, datetime

from kosmo.contracts.auth import (
    InvalidTokenError,
    Principal,
    TokenIssuer,
    TokenPair,
    TokenRevocationStore,
    TokenRevokedError,
    TokenType,
    TokenVerifier,
)


def _seconds_until(expires_at: datetime) -> int:
    delta = expires_at - datetime.now(UTC)
    return max(int(delta.total_seconds()), 0)


@dataclass(frozen=True, slots=True)
class IssueTokenPair:
    issuer: TokenIssuer
    revocation_store: TokenRevocationStore

    async def execute(self, *, subject: str, scopes: frozenset[str]) -> TokenPair:
        access = self.issuer.issue(subject=subject, scopes=scopes, token_type=TokenType.ACCESS)
        refresh = self.issuer.issue(subject=subject, scopes=scopes, token_type=TokenType.REFRESH)
        await self.revocation_store.register_refresh(
            jti=refresh.jti,
            subject=subject,
            ttl_seconds=_seconds_until(refresh.expires_at),
        )
        return TokenPair(access=access, refresh=refresh)


@dataclass(frozen=True, slots=True)
class VerifyAccessToken:
    verifier: TokenVerifier
    revocation_store: TokenRevocationStore

    async def execute(self, token: str) -> Principal:
        claims = self.verifier.verify(token, expected_type=TokenType.ACCESS)
        if await self.revocation_store.is_access_revoked(jti=claims.jti):
            raise TokenRevokedError("Access token revoked")
        return Principal(subject=claims.subject, scopes=claims.scopes)


@dataclass(frozen=True, slots=True)
class RefreshTokenPair:
    issuer: TokenIssuer
    verifier: TokenVerifier
    revocation_store: TokenRevocationStore

    async def execute(self, refresh_token: str, *, scopes: frozenset[str]) -> TokenPair:
        claims = self.verifier.verify(refresh_token, expected_type=TokenType.REFRESH)
        stored_subject = await self.revocation_store.consume_refresh(jti=claims.jti)
        if stored_subject is None or stored_subject != claims.subject:
            raise InvalidTokenError("Refresh token not recognized")

        access = self.issuer.issue(
            subject=claims.subject, scopes=scopes, token_type=TokenType.ACCESS
        )
        new_refresh = self.issuer.issue(
            subject=claims.subject, scopes=scopes, token_type=TokenType.REFRESH
        )
        await self.revocation_store.register_refresh(
            jti=new_refresh.jti,
            subject=claims.subject,
            ttl_seconds=_seconds_until(new_refresh.expires_at),
        )
        return TokenPair(access=access, refresh=new_refresh)


@dataclass(frozen=True, slots=True)
class RevokeSession:
    verifier: TokenVerifier
    revocation_store: TokenRevocationStore

    async def execute(self, *, access_token: str, refresh_token: str | None = None) -> None:
        access_claims = self.verifier.verify(access_token, expected_type=TokenType.ACCESS)
        await self.revocation_store.revoke_access(
            jti=access_claims.jti,
            ttl_seconds=_seconds_until(access_claims.expires_at),
        )
        if refresh_token is None:
            return
        refresh_claims = self.verifier.verify(refresh_token, expected_type=TokenType.REFRESH)
        await self.revocation_store.revoke_refresh(jti=refresh_claims.jti)
