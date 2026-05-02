import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from kosmo.contracts.auth import (
    AuthorizationCode,
    AuthorizationCodeStore,
    InvalidCredentialsError,
    PasswordHasher,
    PkceMethod,
    UserRepository,
)
from kosmo.contracts.telemetry import record_auth_event, traced

_AUTHORIZATION_CODE_TTL_SECONDS = 60


@dataclass(frozen=True, slots=True)
class AuthorizeWithPkce:
    user_repository: UserRepository
    password_hasher: PasswordHasher
    authorization_code_store: AuthorizationCodeStore
    code_ttl_seconds: int = _AUTHORIZATION_CODE_TTL_SECONDS

    @traced("auth.login")
    async def execute(
        self,
        *,
        email: str,
        password: str,
        code_challenge: str,
        scopes: frozenset[str],
    ) -> AuthorizationCode:
        normalized_email = email.strip().lower()
        try:
            user = await self.user_repository.by_email(normalized_email)
            if user is None or not user.is_active:
                raise InvalidCredentialsError("Credenciales inválidas")
            if not self.password_hasher.verify(user.hashed_password, password):
                raise InvalidCredentialsError("Credenciales inválidas")
            if self.password_hasher.needs_rehash(user.hashed_password):
                await self.user_repository.update_password(
                    user_id=user.id,
                    hashed_password=self.password_hasher.hash(password),
                )

            entry = AuthorizationCode(
                code=secrets.token_urlsafe(32),
                subject=user.id,
                code_challenge=code_challenge,
                code_challenge_method=PkceMethod.S256,
                expires_at=datetime.now(UTC) + timedelta(seconds=self.code_ttl_seconds),
                scopes=scopes,
            )
            await self.authorization_code_store.store(entry)
            record_auth_event("login_success", user_id=user.id)
            return entry
        except InvalidCredentialsError:
            record_auth_event("login_failure")
            raise
