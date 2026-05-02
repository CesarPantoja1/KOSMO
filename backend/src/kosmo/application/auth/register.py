from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from kosmo.contracts.auth import (
    PasswordHasher,
    User,
    UserAlreadyExistsError,
    UserRepository,
)
from kosmo.contracts.telemetry import record_auth_event, traced


@dataclass(frozen=True, slots=True)
class RegisterUser:
    user_repository: UserRepository
    password_hasher: PasswordHasher

    @traced("auth.register")
    async def execute(self, *, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        existing = await self.user_repository.by_email(normalized_email)
        if existing is not None:
            raise UserAlreadyExistsError("Email ya registrado")
        user = User(
            id=str(uuid4()),
            email=normalized_email,
            hashed_password=self.password_hasher.hash(password),
            created_at=datetime.now(UTC),
        )
        await self.user_repository.create(user)
        record_auth_event("register_success", user_id=user.id)
        return user
