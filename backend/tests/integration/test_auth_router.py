import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.auth import (  # noqa: E402
    AuthorizeWithPkce,
    ExchangeAuthorizationCode,
    IssueTokenPair,
    RefreshTokenPair,
    RegisterUser,
    RevokeSession,
    VerifyAccessToken,
)
from kosmo.contracts.auth import (  # noqa: E402
    AuthorizationCode,
    RefreshConsumeResult,
    User,
    UserAlreadyExistsError,  # noqa: E402
)
from kosmo.domain.auth import s256_challenge  # noqa: E402
from kosmo.infrastructure.api.routers.auth import router as auth_router  # noqa: E402
from kosmo.infrastructure.api.routers.schemas import router as schemas_router  # noqa: E402
from kosmo.infrastructure.security import (  # noqa: E402
    Argon2idParameters,
    Argon2idPasswordHasher,
    JoseJwtIssuer,
    JoseJwtVerifier,
    JwtSettings,
)

_PRIVATE_PEM = Path(__file__).resolve().parents[2] / ".secrets" / "jwt_private.pem"
_PUBLIC_PEM = Path(__file__).resolve().parents[2] / ".secrets" / "jwt_public.pem"


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}

    async def by_email(self, email: str) -> User | None:
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    async def by_id(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    async def create(self, user: User) -> None:
        if any(u.email == user.email for u in self.users.values()):
            raise UserAlreadyExistsError("Email ya registrado")
        self.users[user.id] = user

    async def update_password(self, *, user_id: str, hashed_password: str) -> None:
        existing = self.users.get(user_id)
        if existing is None:
            return
        self.users[user_id] = User(
            id=existing.id,
            email=existing.email,
            hashed_password=hashed_password,
            created_at=existing.created_at,
            disabled_at=existing.disabled_at,
        )


class InMemoryAuthorizationCodeStore:
    def __init__(self) -> None:
        self.entries: dict[str, AuthorizationCode] = {}

    async def store(self, entry: AuthorizationCode) -> None:
        self.entries[entry.code] = entry

    async def consume(self, code: str) -> AuthorizationCode | None:
        return self.entries.pop(code, None)


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
        return RefreshConsumeResult(subject=entry[0], family_id=entry[1])

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


@pytest.fixture
def client() -> TestClient:
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
    hasher = Argon2idPasswordHasher(
        Argon2idParameters(memory_kib=65536, time_cost=3, parallelism=4)
    )
    user_repository = InMemoryUserRepository()
    code_store = InMemoryAuthorizationCodeStore()
    token_store = InMemoryStore()

    issue_token_pair = IssueTokenPair(issuer=issuer, revocation_store=token_store)

    app = FastAPI()
    app.state.register_user = RegisterUser(
        user_repository=user_repository, password_hasher=hasher
    )
    app.state.authorize_with_pkce = AuthorizeWithPkce(
        user_repository=user_repository,
        password_hasher=hasher,
        authorization_code_store=code_store,
    )
    app.state.exchange_authorization_code = ExchangeAuthorizationCode(
        authorization_code_store=code_store,
        issue_token_pair=issue_token_pair,
    )
    app.state.issue_token_pair = issue_token_pair
    app.state.verify_access_token = VerifyAccessToken(
        verifier=verifier, revocation_store=token_store
    )
    app.state.refresh_token_pair = RefreshTokenPair(
        issuer=issuer, verifier=verifier, revocation_store=token_store
    )
    app.state.revoke_session = RevokeSession(verifier=verifier, revocation_store=token_store)
    app.include_router(auth_router)
    app.include_router(schemas_router)
    return TestClient(app)


def _full_login_flow(
    client: TestClient,
    *,
    email: str = "alice@example.com",
    password: str = "password-12345",
    scopes: list[str] | None = None,
) -> dict[str, Any]:
    verifier = "verifier" * 8
    challenge = s256_challenge(verifier)

    register = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert register.status_code == 201, register.text

    authorize = client.post(
        "/api/v1/auth/authorize",
        json={
            "email": email,
            "password": password,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "scopes": scopes or [],
        },
    )
    assert authorize.status_code == 201, authorize.text
    code = authorize.json()["authorization_code"]

    token = client.post(
        "/api/v1/auth/token",
        json={
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
        },
    )
    assert token.status_code == 200, token.text
    return token.json()


def test_register_returns_201_and_user_payload(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "password-12345"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert "id" in body and "created_at" in body


def test_register_rejects_duplicate_email_with_409(client: TestClient) -> None:
    payload = {"email": "alice@example.com", "password": "password-12345"}
    client.post("/api/v1/auth/register", json=payload)
    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409
    assert second.json()["detail"] == "Email ya registrado"


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_authorize_rejects_invalid_credentials(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "password-12345"},
    )
    response = client.post(
        "/api/v1/auth/authorize",
        json={
            "email": "alice@example.com",
            "password": "wrong-pwd-67890",
            "code_challenge": s256_challenge("verifier" * 8),
            "code_challenge_method": "S256",
            "scopes": [],
        },
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error"] == "invalid_grant"
    assert body["error_description"] == "Credenciales inválidas"


def test_token_exchange_fails_with_wrong_verifier(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "password-12345"},
    )
    challenge = s256_challenge("verifier-A" * 8)
    auth = client.post(
        "/api/v1/auth/authorize",
        json={
            "email": "alice@example.com",
            "password": "password-12345",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "scopes": [],
        },
    )
    code = auth.json()["authorization_code"]
    response = client.post(
        "/api/v1/auth/token",
        json={
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": "verifier-B" * 8,
        },
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_grant"


def test_full_flow_register_authorize_token(client: TestClient) -> None:
    pair = _full_login_flow(client, scopes=["read"])
    assert pair["token_type"] == "Bearer"
    assert pair["access"]["token"]
    assert pair["refresh"]["token"]


def test_refresh_rotates_pair_and_replay_revokes_family(client: TestClient) -> None:
    pair = _full_login_flow(client)

    rotated = client.post(
        "/api/v1/auth/refresh",
        json={"grant_type": "refresh_token", "refresh_token": pair["refresh"]["token"]},
    )
    assert rotated.status_code == 200
    assert rotated.json()["refresh"]["jti"] != pair["refresh"]["jti"]

    replay = client.post(
        "/api/v1/auth/refresh",
        json={"grant_type": "refresh_token", "refresh_token": pair["refresh"]["token"]},
    )
    assert replay.status_code == 401
    assert replay.json()["error"] == "invalid_grant"

    rotated_pair = rotated.json()
    after_revocation = client.post(
        "/api/v1/auth/refresh",
        json={"grant_type": "refresh_token", "refresh_token": rotated_pair["refresh"]["token"]},
    )
    assert after_revocation.status_code == 401


def test_logout_revokes_access_token(client: TestClient) -> None:
    pair = _full_login_flow(client)
    headers = {"Authorization": f"Bearer {pair['access']['token']}"}

    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": pair["refresh"]["token"]},
        headers=headers,
    )
    assert response.status_code == 204

    after = client.get("/api/v1/auth/me", headers=headers)
    assert after.status_code == 401


def test_me_returns_principal_for_valid_token(client: TestClient) -> None:
    pair = _full_login_flow(client, scopes=["read", "write"])
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {pair['access']['token']}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scopes"] == ["read", "write"]


def test_me_rejects_missing_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_schemas_index_lists_models(client: TestClient) -> None:
    response = client.get("/api/v1/schemas")
    assert response.status_code == 200
    schemas = response.json()["schemas"]
    assert "RegisterRequest" in schemas
    assert "TokenPairResponse" in schemas


def test_schemas_returns_json_schema(client: TestClient) -> None:
    response = client.get("/api/v1/schemas/RegisterRequest")
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "RegisterRequest"
    assert "email" in body["properties"]
    assert "password" in body["properties"]


def test_schemas_unknown_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/schemas/Unknown")
    assert response.status_code == 404
