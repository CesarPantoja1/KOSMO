import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.auth import (  # noqa: E402
    AuthorizeWithPkce,
    ExchangeAuthorizationCode,
    IssueTokenPair,
    RegisterUser,
)
from kosmo.contracts.auth import (  # noqa: E402
    AccountLockedError,
    AuthorizationCode,
    AuthorizationCodeError,
    InvalidCredentialsError,
    PkceMismatchError,
    RefreshConsumeResult,
    User,
    UserAlreadyExistsError,
)
from kosmo.domain.auth import s256_challenge  # noqa: E402
from kosmo.infrastructure.security import (  # noqa: E402
    Argon2idParameters,
    Argon2idPasswordHasher,
    JoseJwtIssuer,
    JoseJwtVerifier,
    JwtSettings,
)

# Par de llaves RSA efímero — generado una vez para toda la sesión de pruebas
_RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)

_PRIVATE_PEM: str = _RSA_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption(),
).decode()

_PUBLIC_PEM: str = (
    _RSA_KEY.public_key()
    .public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    .decode()
)

_MAX_FAILURES = 10
_LOCKOUT_SECONDS = 900


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


class InMemoryLoginAttemptStore:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    async def record_failure(self, identifier: str) -> None:
        self._counts[identifier] = self._counts.get(identifier, 0) + 1

    async def clear(self, identifier: str) -> None:
        self._counts.pop(identifier, None)

    async def lockout_seconds(self, identifier: str) -> int | None:
        count = self._counts.get(identifier, 0)
        return _LOCKOUT_SECONDS if count >= _MAX_FAILURES else None


def _hasher() -> Argon2idPasswordHasher:
    return Argon2idPasswordHasher(Argon2idParameters(memory_kib=65536, time_cost=3, parallelism=4))


def _issuer_pair() -> tuple[JoseJwtIssuer, JoseJwtVerifier]:
    settings = JwtSettings(
        algorithm="RS256",
        issuer="kosmo-test",
        audience="kosmo-test",
        access_ttl_seconds=120,
        refresh_ttl_seconds=600,
    )
    return (
        JoseJwtIssuer(private_key_pem=_PRIVATE_PEM, settings=settings),
        JoseJwtVerifier(public_key_pem=_PUBLIC_PEM, settings=settings),
    )


@pytest.mark.asyncio
async def test_register_creates_user_with_argon2_hash() -> None:
    repo = InMemoryUserRepository()
    hasher = _hasher()
    register = RegisterUser(user_repository=repo, password_hasher=hasher)

    user = await register.execute(email="alice@example.com", password="password-12345")

    assert user.email == "alice@example.com"
    assert user.hashed_password.startswith("$argon2id$")
    assert hasher.verify(user.hashed_password, "password-12345") is True


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email() -> None:
    repo = InMemoryUserRepository()
    register = RegisterUser(user_repository=repo, password_hasher=_hasher())
    await register.execute(email="alice@example.com", password="password-12345")

    with pytest.raises(UserAlreadyExistsError):
        await register.execute(email="alice@example.com", password="another-pwd-67890")


@pytest.mark.asyncio
async def test_authorize_with_valid_credentials_emits_code() -> None:
    repo = InMemoryUserRepository()
    hasher = _hasher()
    code_store = InMemoryAuthorizationCodeStore()
    register = RegisterUser(user_repository=repo, password_hasher=hasher)
    authorize = AuthorizeWithPkce(
        user_repository=repo,
        password_hasher=hasher,
        authorization_code_store=code_store,
        login_attempt_store=InMemoryLoginAttemptStore(),
    )

    await register.execute(email="bob@example.com", password="password-12345")
    challenge = s256_challenge("verifier" * 8)

    entry = await authorize.execute(
        email="bob@example.com",
        password="password-12345",
        code_challenge=challenge,
        scopes=frozenset({"read"}),
    )

    assert entry.code in code_store.entries
    assert entry.scopes == frozenset({"read"})
    assert entry.expires_at > datetime.now(UTC)


@pytest.mark.asyncio
async def test_authorize_with_wrong_password_raises() -> None:
    repo = InMemoryUserRepository()
    hasher = _hasher()
    code_store = InMemoryAuthorizationCodeStore()
    register = RegisterUser(user_repository=repo, password_hasher=hasher)
    authorize = AuthorizeWithPkce(
        user_repository=repo,
        password_hasher=hasher,
        authorization_code_store=code_store,
        login_attempt_store=InMemoryLoginAttemptStore(),
    )
    await register.execute(email="bob@example.com", password="password-12345")

    with pytest.raises(InvalidCredentialsError):
        await authorize.execute(
            email="bob@example.com",
            password="wrong-pwd-67890",
            code_challenge=s256_challenge("verifier" * 8),
            scopes=frozenset(),
        )


@pytest.mark.asyncio
async def test_authorize_records_failure_on_bad_credentials() -> None:
    repo = InMemoryUserRepository()
    hasher = _hasher()
    attempt_store = InMemoryLoginAttemptStore()
    register = RegisterUser(user_repository=repo, password_hasher=hasher)
    authorize = AuthorizeWithPkce(
        user_repository=repo,
        password_hasher=hasher,
        authorization_code_store=InMemoryAuthorizationCodeStore(),
        login_attempt_store=attempt_store,
    )
    await register.execute(email="dave@example.com", password="password-12345")

    for _ in range(3):
        with pytest.raises(InvalidCredentialsError):
            await authorize.execute(
                email="dave@example.com",
                password="wrong",
                code_challenge=s256_challenge("verifier" * 8),
                scopes=frozenset(),
            )

    assert attempt_store._counts.get("dave@example.com") == 3


@pytest.mark.asyncio
async def test_authorize_locks_account_after_max_failures() -> None:
    repo = InMemoryUserRepository()
    hasher = _hasher()
    attempt_store = InMemoryLoginAttemptStore()
    register = RegisterUser(user_repository=repo, password_hasher=hasher)
    authorize = AuthorizeWithPkce(
        user_repository=repo,
        password_hasher=hasher,
        authorization_code_store=InMemoryAuthorizationCodeStore(),
        login_attempt_store=attempt_store,
    )
    await register.execute(email="eve@example.com", password="password-12345")
    challenge = s256_challenge("verifier" * 8)

    for _ in range(_MAX_FAILURES):
        with pytest.raises(InvalidCredentialsError):
            await authorize.execute(
                email="eve@example.com",
                password="wrong",
                code_challenge=challenge,
                scopes=frozenset(),
            )

    with pytest.raises(AccountLockedError) as exc_info:
        await authorize.execute(
            email="eve@example.com",
            password="wrong",
            code_challenge=challenge,
            scopes=frozenset(),
        )
    assert exc_info.value.seconds_remaining == _LOCKOUT_SECONDS


@pytest.mark.asyncio
async def test_authorize_clears_attempts_on_successful_login() -> None:
    repo = InMemoryUserRepository()
    hasher = _hasher()
    attempt_store = InMemoryLoginAttemptStore()
    code_store = InMemoryAuthorizationCodeStore()
    register = RegisterUser(user_repository=repo, password_hasher=hasher)
    authorize = AuthorizeWithPkce(
        user_repository=repo,
        password_hasher=hasher,
        authorization_code_store=code_store,
        login_attempt_store=attempt_store,
    )
    await register.execute(email="frank@example.com", password="password-12345")
    challenge = s256_challenge("verifier" * 8)

    for _ in range(5):
        with pytest.raises(InvalidCredentialsError):
            await authorize.execute(
                email="frank@example.com",
                password="wrong",
                code_challenge=challenge,
                scopes=frozenset(),
            )

    assert attempt_store._counts.get("frank@example.com") == 5

    await authorize.execute(
        email="frank@example.com",
        password="password-12345",
        code_challenge=challenge,
        scopes=frozenset(),
    )

    assert attempt_store._counts.get("frank@example.com") is None


@pytest.mark.asyncio
async def test_exchange_consumes_code_and_emits_pair() -> None:
    repo = InMemoryUserRepository()
    hasher = _hasher()
    code_store = InMemoryAuthorizationCodeStore()
    token_store = InMemoryStore()
    issuer, _ = _issuer_pair()

    register = RegisterUser(user_repository=repo, password_hasher=hasher)
    authorize = AuthorizeWithPkce(
        user_repository=repo,
        password_hasher=hasher,
        authorization_code_store=code_store,
        login_attempt_store=InMemoryLoginAttemptStore(),
    )
    issue = IssueTokenPair(issuer=issuer, revocation_store=token_store)
    exchange = ExchangeAuthorizationCode(
        authorization_code_store=code_store,
        issue_token_pair=issue,
    )

    await register.execute(email="bob@example.com", password="password-12345")
    verifier = "verifier" * 8
    entry = await authorize.execute(
        email="bob@example.com",
        password="password-12345",
        code_challenge=s256_challenge(verifier),
        scopes=frozenset({"read"}),
    )

    pair = await exchange.execute(code=entry.code, code_verifier=verifier)

    assert pair.access.token
    assert pair.refresh.token
    assert pair.access.family_id is not None
    assert pair.access.family_id == pair.refresh.family_id
    assert entry.code not in code_store.entries

    with pytest.raises(AuthorizationCodeError):
        await exchange.execute(code=entry.code, code_verifier=verifier)


@pytest.mark.asyncio
async def test_exchange_rejects_mismatched_verifier() -> None:
    repo = InMemoryUserRepository()
    hasher = _hasher()
    code_store = InMemoryAuthorizationCodeStore()
    token_store = InMemoryStore()
    issuer, _ = _issuer_pair()
    register = RegisterUser(user_repository=repo, password_hasher=hasher)
    authorize = AuthorizeWithPkce(
        user_repository=repo,
        password_hasher=hasher,
        authorization_code_store=code_store,
        login_attempt_store=InMemoryLoginAttemptStore(),
    )
    exchange = ExchangeAuthorizationCode(
        authorization_code_store=code_store,
        issue_token_pair=IssueTokenPair(issuer=issuer, revocation_store=token_store),
    )

    await register.execute(email="bob@example.com", password="password-12345")
    entry = await authorize.execute(
        email="bob@example.com",
        password="password-12345",
        code_challenge=s256_challenge("verifier-A" * 8),
        scopes=frozenset(),
    )

    with pytest.raises(PkceMismatchError):
        await exchange.execute(code=entry.code, code_verifier="verifier-B" * 8)
