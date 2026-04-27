import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.auth import (  # noqa: E402
    IssueTokenPair,
    RefreshTokenPair,
    RevokeSession,
    VerifyAccessToken,
)
from kosmo.infrastructure.api.routers.auth_demo import router as auth_demo_router  # noqa: E402
from kosmo.infrastructure.security import JoseJwtIssuer, JoseJwtVerifier, JwtSettings  # noqa: E402

_PRIVATE_PEM = Path(__file__).resolve().parents[2] / ".secrets" / "jwt_private.pem"
_PUBLIC_PEM = Path(__file__).resolve().parents[2] / ".secrets" / "jwt_public.pem"


class InMemoryStore:
    def __init__(self) -> None:
        self.refresh: dict[str, str] = {}
        self.revoked: set[str] = set()

    async def register_refresh(self, *, jti: str, subject: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        self.refresh[jti] = subject

    async def consume_refresh(self, *, jti: str) -> str | None:
        return self.refresh.pop(jti, None)

    async def revoke_access(self, *, jti: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        self.revoked.add(jti)

    async def is_access_revoked(self, *, jti: str) -> bool:
        return jti in self.revoked

    async def revoke_refresh(self, *, jti: str) -> None:
        self.refresh.pop(jti, None)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    settings = JwtSettings(
        algorithm="RS256",
        issuer="kosmo-test",
        audience="kosmo-test",
        access_ttl_seconds=120,
        refresh_ttl_seconds=600,
    )
    issuer = JoseJwtIssuer(
        private_key_pem=_PRIVATE_PEM.read_text(encoding="utf-8"), settings=settings
    )
    verifier = JoseJwtVerifier(
        public_key_pem=_PUBLIC_PEM.read_text(encoding="utf-8"), settings=settings
    )
    store = InMemoryStore()
    app.state.issue_token_pair = IssueTokenPair(issuer=issuer, revocation_store=store)
    app.state.verify_access_token = VerifyAccessToken(verifier=verifier, revocation_store=store)
    app.state.refresh_token_pair = RefreshTokenPair(
        issuer=issuer, verifier=verifier, revocation_store=store
    )
    app.state.revoke_session = RevokeSession(verifier=verifier, revocation_store=store)
    app.include_router(auth_demo_router)
    return TestClient(app)


def _issue(client: TestClient, scopes: list[str] | None = None) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/demo/token",
        json={"subject": "user-42", "scopes": scopes or []},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_protected_route_requires_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/demo/me")
    assert response.status_code == 401
    assert response.headers.get("www-authenticate", "").startswith("Bearer")


def test_issued_token_unlocks_protected_route(client: TestClient) -> None:
    pair = _issue(client, ["read"])
    response = client.get(
        "/api/v1/auth/demo/me",
        headers={"Authorization": f"Bearer {pair['access']['token']}"},
    )
    assert response.status_code == 200
    assert response.json() == {"subject": "user-42", "scopes": ["read"]}


def test_scope_guard_returns_403(client: TestClient) -> None:
    pair = _issue(client, ["read"])
    response = client.get(
        "/api/v1/auth/demo/admin",
        headers={"Authorization": f"Bearer {pair['access']['token']}"},
    )
    assert response.status_code == 403


def test_admin_scope_unlocks_admin_route(client: TestClient) -> None:
    pair = _issue(client, ["admin"])
    response = client.get(
        "/api/v1/auth/demo/admin",
        headers={"Authorization": f"Bearer {pair['access']['token']}"},
    )
    assert response.status_code == 200


def test_refresh_returns_new_pair_and_invalidates_old(client: TestClient) -> None:
    pair = _issue(client, ["read"])
    refresh = client.post(
        "/api/v1/auth/demo/refresh",
        json={"refresh_token": pair["refresh"]["token"], "scopes": ["read"]},
    )
    assert refresh.status_code == 200
    rotated = refresh.json()
    assert rotated["refresh"]["jti"] != pair["refresh"]["jti"]

    replay = client.post(
        "/api/v1/auth/demo/refresh",
        json={"refresh_token": pair["refresh"]["token"], "scopes": ["read"]},
    )
    assert replay.status_code == 401


def test_logout_revokes_access_token(client: TestClient) -> None:
    pair = _issue(client, ["read"])
    headers = {"Authorization": f"Bearer {pair['access']['token']}"}

    logout = client.post(
        "/api/v1/auth/demo/logout",
        json={"refresh_token": pair["refresh"]["token"]},
        headers=headers,
    )
    assert logout.status_code == 204

    response = client.get("/api/v1/auth/demo/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Token revoked"


def test_garbage_token_is_rejected(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/demo/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401
