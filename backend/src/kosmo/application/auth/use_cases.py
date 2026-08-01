from dataclasses import dataclass
from datetime import UTC, datetime

from ulid import ULID

from kosmo.contracts.audit import AuditEvent, AuditEventSink, AuditOutcome
from kosmo.contracts.auth import (
    InvalidTokenError,
    Principal,
    TokenIssuer,
    TokenPair,
    TokenReusedError,
    TokenRevocationStore,
    TokenRevokedError,
    TokenType,
    TokenVerifier,
)
from kosmo.contracts.telemetry import record_auth_event, traced


def _seconds_until(expires_at: datetime) -> int:
    delta = expires_at - datetime.now(UTC)
    return max(int(delta.total_seconds()), 0)


@dataclass(frozen=True, slots=True)
class IssueTokenPair:
    issuer: TokenIssuer
    revocation_store: TokenRevocationStore

    async def execute(
        self,
        *,
        subject: str,
        scopes: frozenset[str],
        family_id: str | None = None,
    ) -> TokenPair:
        family = family_id or ULID().hex
        access = self.issuer.issue(subject=subject, scopes=scopes, token_type=TokenType.ACCESS, family_id=family)
        refresh = self.issuer.issue(subject=subject, scopes=scopes, token_type=TokenType.REFRESH, family_id=family)
        await self.revocation_store.register_refresh(
            jti=refresh.jti,
            subject=subject,
            ttl_seconds=_seconds_until(refresh.expires_at),
            family_id=family,
        )
        return TokenPair(access=access, refresh=refresh)


_JTI_CACHE: dict[str, bool] = {}
_JTI_CACHE_MAX = 1000


def _jti_is_cached_revoked(jti: str) -> bool | None:
    return _JTI_CACHE.get(jti)


def _jti_cache_set(jti: str, revoked: bool) -> None:
    if len(_JTI_CACHE) >= _JTI_CACHE_MAX:
        _JTI_CACHE.pop(next(iter(_JTI_CACHE)))
    _JTI_CACHE[jti] = revoked


@dataclass(frozen=True, slots=True)
class VerifyAccessToken:
    verifier: TokenVerifier
    revocation_store: TokenRevocationStore

    async def execute(self, token: str) -> Principal:
        claims = self.verifier.verify(token, expected_type=TokenType.ACCESS)

        cached = _jti_is_cached_revoked(claims.jti)
        if cached:
            raise TokenRevokedError("Access token revoked")
        if cached is False and claims.family_id is not None:
            family_cached = _jti_is_cached_revoked(claims.family_id)
            if family_cached:
                raise TokenRevokedError("Session revoked")

        if await self.revocation_store.is_access_revoked(jti=claims.jti):
            _jti_cache_set(claims.jti, True)
            raise TokenRevokedError("Access token revoked")
        if claims.family_id is not None and not await self.revocation_store.is_family_alive(family_id=claims.family_id):
            _jti_cache_set(claims.family_id, True)
            raise TokenRevokedError("Session revoked")

        _jti_cache_set(claims.jti, False)
        return Principal(subject=claims.subject, scopes=claims.scopes)


@dataclass(frozen=True, slots=True)
class RefreshTokenPair:
    issuer: TokenIssuer
    verifier: TokenVerifier
    revocation_store: TokenRevocationStore
    audit_sink: AuditEventSink

    @traced("auth.token_refresh")
    async def execute(self, refresh_token: str, *, scopes: frozenset[str]) -> TokenPair:
        claims = self.verifier.verify(refresh_token, expected_type=TokenType.REFRESH)
        consumed = await self.revocation_store.consume_refresh(jti=claims.jti)
        if consumed is None:
            if claims.family_id is not None and await self.revocation_store.is_family_alive(family_id=claims.family_id):
                await self.revocation_store.revoke_family(family_id=claims.family_id)
                await self.audit_sink.record(
                    AuditEvent(
                        event_type="auth.token_reused",
                        outcome=AuditOutcome.FAILURE,
                        occurred_at=datetime.now(UTC),
                        actor_id=claims.subject,
                        metadata={"reason": "refresh_token_reused"},
                    )
                )
                raise TokenReusedError("Refresh token reusado, sesión revocada")
            raise InvalidTokenError("Refresh token not recognized")
        if consumed.subject != claims.subject:
            if claims.family_id is not None:
                await self.revocation_store.revoke_family(family_id=claims.family_id)
            raise InvalidTokenError("Refresh token subject mismatch")

        family = consumed.family_id or claims.family_id
        if family is not None and not await self.revocation_store.is_family_alive(family_id=family):
            raise TokenRevokedError("Sesión revocada")
        access = self.issuer.issue(
            subject=claims.subject,
            scopes=scopes,
            token_type=TokenType.ACCESS,
            family_id=family,
        )
        new_refresh = self.issuer.issue(
            subject=claims.subject,
            scopes=scopes,
            token_type=TokenType.REFRESH,
            family_id=family,
        )
        await self.revocation_store.register_refresh(
            jti=new_refresh.jti,
            subject=claims.subject,
            ttl_seconds=_seconds_until(new_refresh.expires_at),
            family_id=family,
        )
        await self.audit_sink.record(
            AuditEvent(
                event_type="auth.token_refresh",
                outcome=AuditOutcome.SUCCESS,
                occurred_at=datetime.now(UTC),
                actor_id=claims.subject,
            )
        )
        record_auth_event("token_refresh", user_id=claims.subject)
        return TokenPair(access=access, refresh=new_refresh)


@dataclass(frozen=True, slots=True)
class RevokeSession:
    verifier: TokenVerifier
    revocation_store: TokenRevocationStore
    audit_sink: AuditEventSink

    @traced("auth.logout")
    async def execute(self, *, access_token: str, refresh_token: str | None = None) -> None:
        access_claims = self.verifier.verify(access_token, expected_type=TokenType.ACCESS)
        await self.revocation_store.revoke_access(
            jti=access_claims.jti,
            ttl_seconds=_seconds_until(access_claims.expires_at),
        )
        if access_claims.family_id is not None:
            await self.revocation_store.revoke_family(family_id=access_claims.family_id)
        if refresh_token is not None:
            refresh_claims = self.verifier.verify(refresh_token, expected_type=TokenType.REFRESH)
            await self.revocation_store.revoke_refresh(jti=refresh_claims.jti)
            if refresh_claims.family_id is not None:
                await self.revocation_store.revoke_family(family_id=refresh_claims.family_id)
        await self.audit_sink.record(
            AuditEvent(
                event_type="auth.logout",
                outcome=AuditOutcome.SUCCESS,
                occurred_at=datetime.now(UTC),
                actor_id=access_claims.subject,
            )
        )
        record_auth_event("logout", user_id=access_claims.subject)
