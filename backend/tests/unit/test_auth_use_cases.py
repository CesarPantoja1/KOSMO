import importlib
import sys
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.auth import (  # noqa: E402
    IssueTokenPair,
    RefreshTokenPair,
    RevokeSession,
    VerifyAccessToken,
)
from kosmo.contracts.auth import (  # noqa: E402
    InvalidTokenError,
    IssuedToken,
    Principal,
    RefreshConsumeResult,
    TokenClaims,
    TokenExpiredError,
    TokenPair,
    TokenReusedError,
    TokenRevokedError,
    TokenType,
)

security = importlib.import_module("kosmo.infrastructure.security")
JoseJwtIssuer = security.JoseJwtIssuer
JoseJwtVerifier = security.JoseJwtVerifier
JwtSettings = security.JwtSettings


_PRIVATE_PEM = Path(__file__).resolve().parents[2] / ".secrets" / "jwt_private.pem"
_PUBLIC_PEM = Path(__file__).resolve().parents[2] / ".secrets" / "jwt_public.pem"


class InMemoryStore:
    def __init__(self) -> None:
        self.refresh: dict[str, tuple[str, str | None]] = {}
        self.revoked_access: set[str] = set()
        self.families: set[str] = set()

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
        self.refresh[jti] = (subject, family_id)
        if family_id is not None:
            self.families.add(family_id)

    async def consume_refresh(self, *, jti: str) -> RefreshConsumeResult | None:
        entry = self.refresh.pop(jti, None)
        if entry is None:
            return None
        subject, family_id = entry
        return RefreshConsumeResult(subject=subject, family_id=family_id)

    async def revoke_access(self, *, jti: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        self.revoked_access.add(jti)

    async def is_access_revoked(self, *, jti: str) -> bool:
        return jti in self.revoked_access

    async def revoke_refresh(self, *, jti: str) -> None:
        self.refresh.pop(jti, None)

    async def is_family_alive(self, *, family_id: str) -> bool:
        return family_id in self.families

    async def revoke_family(self, *, family_id: str) -> None:
        self.families.discard(family_id)
        for jti in list(self.refresh):
            if self.refresh[jti][1] == family_id:
                del self.refresh[jti]


def _build_codec() -> tuple[JoseJwtIssuer, JoseJwtVerifier]:
    settings = JwtSettings(
        algorithm="RS256",
        issuer="kosmo-test",
        audience="kosmo-test",
        access_ttl_seconds=60,
        refresh_ttl_seconds=300,
    )
    private = _PRIVATE_PEM.read_text(encoding="utf-8")
    public = _PUBLIC_PEM.read_text(encoding="utf-8")
    return JoseJwtIssuer(private_key_pem=private, settings=settings), JoseJwtVerifier(
        public_key_pem=public, settings=settings
    )


@pytest.mark.asyncio
async def test_issue_then_verify_returns_principal() -> None:
    issuer, verifier = _build_codec()
    store = InMemoryStore()
    issue = IssueTokenPair(issuer=issuer, revocation_store=store)
    verify = VerifyAccessToken(verifier=verifier, revocation_store=store)

    pair: TokenPair = await issue.execute(subject="user-1", scopes=frozenset({"read"}))
    principal: Principal = await verify.execute(pair.access.token)

    assert principal.subject == "user-1"
    assert principal.scopes == frozenset({"read"})
    assert pair.refresh.jti in store.refresh


@pytest.mark.asyncio
async def test_revoked_access_rejected() -> None:
    issuer, verifier = _build_codec()
    store = InMemoryStore()
    issue = IssueTokenPair(issuer=issuer, revocation_store=store)
    verify = VerifyAccessToken(verifier=verifier, revocation_store=store)
    revoke = RevokeSession(verifier=verifier, revocation_store=store)

    pair = await issue.execute(subject="user-1", scopes=frozenset())
    await revoke.execute(access_token=pair.access.token, refresh_token=pair.refresh.token)

    with pytest.raises(TokenRevokedError):
        await verify.execute(pair.access.token)
    assert pair.refresh.jti not in store.refresh


@pytest.mark.asyncio
async def test_refresh_rotates_pair() -> None:
    issuer, verifier = _build_codec()
    store = InMemoryStore()
    issue = IssueTokenPair(issuer=issuer, revocation_store=store)
    refresh_uc = RefreshTokenPair(issuer=issuer, verifier=verifier, revocation_store=store)

    original = await issue.execute(subject="user-1", scopes=frozenset({"read"}))
    rotated = await refresh_uc.execute(original.refresh.token, scopes=frozenset({"read"}))

    assert rotated.refresh.jti != original.refresh.jti
    assert original.refresh.jti not in store.refresh
    assert rotated.refresh.jti in store.refresh

    with pytest.raises(TokenReusedError):
        await refresh_uc.execute(original.refresh.token, scopes=frozenset({"read"}))


@pytest.mark.asyncio
async def test_access_token_used_as_refresh_is_rejected() -> None:
    issuer, verifier = _build_codec()
    store = InMemoryStore()
    issue = IssueTokenPair(issuer=issuer, revocation_store=store)
    refresh_uc = RefreshTokenPair(issuer=issuer, verifier=verifier, revocation_store=store)

    pair = await issue.execute(subject="user-1", scopes=frozenset())

    with pytest.raises(InvalidTokenError):
        await refresh_uc.execute(pair.access.token, scopes=frozenset())


def test_expired_token_raises() -> None:
    issuer, verifier = _build_codec()
    issued = issuer.issue(
        subject="user-1", scopes=frozenset(), token_type=TokenType.ACCESS
    )
    _ = cast(IssuedToken, issued)

    expired_settings = JwtSettings(
        algorithm="RS256",
        issuer="kosmo-test",
        audience="kosmo-test",
        access_ttl_seconds=-10,
        refresh_ttl_seconds=-10,
    )
    expired_issuer = JoseJwtIssuer(
        private_key_pem=_PRIVATE_PEM.read_text(encoding="utf-8"), settings=expired_settings
    )
    expired_token = expired_issuer.issue(
        subject="user-1", scopes=frozenset(), token_type=TokenType.ACCESS
    )

    with pytest.raises(TokenExpiredError):
        verifier.verify(expired_token.token, expected_type=TokenType.ACCESS)


def test_verifier_rejects_tampered_token() -> None:
    _, verifier = _build_codec()
    bogus = "eyJhbGciOiJSUzI1NiJ9.bm90LWEtdG9rZW4.signature"

    with pytest.raises(InvalidTokenError):
        verifier.verify(bogus, expected_type=TokenType.ACCESS)


def test_token_claims_dataclass_is_immutable() -> None:
    claims = TokenClaims(
        subject="x",
        jti="j",
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(seconds=60),
        token_type=TokenType.ACCESS,
        scopes=frozenset({"a"}),
    )
    with pytest.raises(FrozenInstanceError):
        claims.subject = "y"  # type: ignore[misc]
