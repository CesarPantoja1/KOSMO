from __future__ import annotations

import os
from base64 import urlsafe_b64encode
from secrets import token_bytes
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Par de llaves RSA efímero generado una vez por sesión de pruebas (sin archivos en disco).
_rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

_PRIVATE_KEY_PEM: str = _rsa_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption(),
).decode()

_PUBLIC_KEY_PEM: str = (
    _rsa_key.public_key()
    .public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    .decode()
)

_FERNET_KEY: str = urlsafe_b64encode(token_bytes(32)).decode()

_TEST_DEFAULTS: dict[str, str] = {
    "ENV": "development",
    "LOG_LEVEL": "DEBUG",
    "JWT_PRIVATE_KEY_PEM": _PRIVATE_KEY_PEM,
    "JWT_PUBLIC_KEY_PEM": _PUBLIC_KEY_PEM,
    "FERNET_MASTER_KEY": _FERNET_KEY,
    "LLM_PROVIDER": "noop",
    "LLM_MODEL": "noop",
    "DATABASE_URL": "postgresql+asyncpg://kosmo:kosmo@localhost:5432/kosmo_test",
    "MONGO_URL": "mongodb://localhost:27017/kosmo_test",
    "REDIS_URL": "redis://localhost:6379/1",
    "OTEL_SERVICE_NAME": "kosmo-backend-test",
    "OTEL_ENVIRONMENT": "development",
}

for _key, _value in _TEST_DEFAULTS.items():
    os.environ.setdefault(_key, _value)


# =============================================================================
# Stubs compartidos — implementaciones en memoria de todos los puertos
# =============================================================================


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.users: dict[str, Any] = {}

    async def by_email(self, email: str) -> Any | None:
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    async def by_id(self, user_id: str) -> Any | None:
        return self.users.get(user_id)

    async def create(self, user: Any) -> None:
        from kosmo.contracts.auth import UserAlreadyExistsError

        if any(u.email == user.email for u in self.users.values()):
            raise UserAlreadyExistsError("Email ya registrado")
        self.users[user.id] = user

    async def update_password(self, *, user_id: str, hashed_password: str) -> None:
        existing = self.users.get(user_id)
        if existing is None:
            return
        from kosmo.contracts.auth import User as U

        self.users[user_id] = U(
            id=existing.id,
            email=existing.email,
            hashed_password=hashed_password,
            created_at=existing.created_at,
            disabled_at=existing.disabled_at,
        )


class InMemoryAuthorizationCodeStore:
    def __init__(self) -> None:
        self.entries: dict[str, Any] = {}

    async def store(self, entry: Any) -> None:
        self.entries[entry.code] = entry

    async def consume(self, code: str) -> Any | None:
        return self.entries.pop(code, None)


class InMemoryTokenStore:
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

    async def consume_refresh(self, *, jti: str) -> Any | None:
        from kosmo.contracts.auth import RefreshConsumeResult

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
        for jti in list(self.refresh):
            if self.refresh[jti][1] == family_id:
                del self.refresh[jti]


class InMemoryLoginAttemptStore:
    def __init__(self, max_failures: int = 10, lockout_seconds_val: int = 900) -> None:
        self._counts: dict[str, int] = {}
        self._max_failures = max_failures
        self._lockout_seconds = lockout_seconds_val

    async def record_failure(self, identifier: str) -> None:
        self._counts[identifier] = self._counts.get(identifier, 0) + 1

    async def clear(self, identifier: str) -> None:
        self._counts.pop(identifier, None)

    async def lockout_seconds(self, identifier: str) -> int | None:
        count = self._counts.get(identifier, 0)
        return self._lockout_seconds if count >= self._max_failures else None


class InMemoryAuditEventSink:
    def __init__(self) -> None:
        self.events: list[Any] = []

    async def record(self, event: Any) -> None:
        self.events.append(event)


class InMemoryUserPreferenceRepository:
    def __init__(self) -> None:
        self._preferences: list[Any] = []
        self._usage_counts: dict[str, int] = {}

    async def add(self, preference: Any) -> None:
        self._preferences.append(preference)

    async def get_by_user(
        self,
        user_id: str,
        project_id: Any | None = None,
        document_type: str | None = None,
        limit: int = 20,
    ) -> list[Any]:
        result = [p for p in self._preferences if p.user_id == user_id]
        if project_id is not None:
            result = [p for p in result if p.project_id == project_id or p.project_id is None]
        if document_type is not None:
            result = [p for p in result if p.document_type == document_type]
        result.sort(key=lambda p: (p.usage_count, p.created_at), reverse=True)
        return result[:limit]

    async def increment_usage(self, preference_ids: list[str]) -> None:
        for pid in preference_ids:
            self._usage_counts[pid] = self._usage_counts.get(pid, 0) + 1

    async def delete(self, preference_id: str) -> None:
        self._preferences = [p for p in self._preferences if p.id != preference_id]


class InMemoryFeatureRepository:
    def __init__(self) -> None:
        self._features: dict[str, Any] = {}
        self._requirements_docs: dict[str, dict] = {}

    async def add(self, feature: Any) -> None:
        self._features[feature.id] = feature

    async def get_by_project(self, project_id: str) -> list[Any]:
        return [f for f in self._features.values() if f.project_id == project_id]

    async def get(self, feature_id: str) -> Any | None:
        return self._features.get(feature_id)

    async def get_by_slug(self, project_id: str, slug: str) -> Any | None:
        for f in self._features.values():
            if f.project_id == project_id and f.slug == slug:
                return f
        return None

    async def delete(self, feature_id: str) -> None:
        self._features.pop(feature_id, None)

    async def update(self, feature: Any) -> None:
        self._features[feature.id] = feature

    async def update_requirements(self, feature_id: str, requirements: Any) -> None:
        pass

    async def update_requirements_document(self, feature_id: str, document: dict) -> None:
        self._requirements_docs[feature_id] = document

    async def get_requirements_document(self, feature_id: str) -> dict | None:
        return self._requirements_docs.get(feature_id)


class ControlledLLMClient:
    """LLMClient programable: cada test define la respuesta exacta que debe emitir."""

    def __init__(self) -> None:
        self._response: str = "{}"
        self._should_fail: bool = False
        self._exception: Exception | None = None
        self._call_count: int = 0
        self._last_prompt: Any = None

    def set_response(self, content: str) -> None:
        self._response = content
        self._should_fail = False
        self._exception = None

    def set_failure(self, exception: Exception | None = None) -> None:
        self._should_fail = True
        self._exception = exception or Exception("LLM failure")

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def last_prompt(self) -> Any:
        return self._last_prompt

    async def complete(
        self,
        prompt: Any,
        response_schema: type | None = None,
        temperature: float = 0,
        max_tokens: int | None = None,
        cache_key: str | None = None,
    ) -> Any:
        from kosmo.contracts.llm.ports import LLMResponse, LLMUsage

        self._call_count += 1
        self._last_prompt = prompt

        if self._should_fail:
            raise self._exception

        return LLMResponse(
            content=self._response,
            usage=LLMUsage(prompt_tokens=100, completion_tokens=200, total_tokens=300),
            model_id="controlled-test",
        )

    async def stream(
        self,
        prompt: Any,
        temperature: float = 0,
        max_tokens: int | None = None,
    ) -> object:
        class _FakeStream:
            async def __aiter__(self) -> _FakeStream:
                return self

            async def __anext__(self) -> str:
                raise StopAsyncIteration

        return _FakeStream()


# =============================================================================
# Fixtures de pytest
# =============================================================================


@pytest.fixture
def private_key_pem() -> str:
    return _PRIVATE_KEY_PEM


@pytest.fixture
def public_key_pem() -> str:
    return _PUBLIC_KEY_PEM


@pytest.fixture
def in_memory_user_repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def in_memory_auth_code_store() -> InMemoryAuthorizationCodeStore:
    return InMemoryAuthorizationCodeStore()


@pytest.fixture
def in_memory_token_store() -> InMemoryTokenStore:
    return InMemoryTokenStore()


@pytest.fixture
def in_memory_login_attempt_store() -> InMemoryLoginAttemptStore:
    return InMemoryLoginAttemptStore()


@pytest.fixture
def in_memory_audit_sink() -> InMemoryAuditEventSink:
    return InMemoryAuditEventSink()


@pytest.fixture
def in_memory_preference_repo() -> InMemoryUserPreferenceRepository:
    return InMemoryUserPreferenceRepository()


@pytest.fixture
def in_memory_feature_repo() -> InMemoryFeatureRepository:
    return InMemoryFeatureRepository()


@pytest.fixture
def controlled_llm_client() -> ControlledLLMClient:
    return ControlledLLMClient()


@pytest.fixture
def graph_deps(
    controlled_llm_client: ControlledLLMClient,
    in_memory_preference_repo: InMemoryUserPreferenceRepository,
) -> Any:
    from kosmo.contracts.orchestration.graph_deps import GraphDependencies

    return GraphDependencies(
        llm_client=controlled_llm_client,
        preference_repo=in_memory_preference_repo,
    )


@pytest.fixture
def kosmo_state() -> Any:
    from kosmo.contracts.sdd.state import KOSMOState

    state = KOSMOState(project_id="prj_test01", user_id="usr_test01")
    state.shared_scratchpad["current_feature_title"] = "Test Feature"
    state.shared_scratchpad["current_feature_description"] = "Test description"
    return state
