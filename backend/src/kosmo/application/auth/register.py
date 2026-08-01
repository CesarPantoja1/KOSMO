from dataclasses import dataclass
from datetime import UTC, datetime

from kosmo.contracts.audit import AuditEvent, AuditEventSink, AuditOutcome
from kosmo.contracts.auth import (
    PasswordHasher,
    User,
    UserAlreadyExistsError,
    UserRepository,
)
from kosmo.contracts.telemetry import record_auth_event, traced
from kosmo.domain.sdd.id_generator import IdGenerator


@dataclass(frozen=True, slots=True)
class RegisterUser:
    user_repository: UserRepository
    password_hasher: PasswordHasher
    audit_sink: AuditEventSink

    @traced("auth.register")
    async def execute(self, *, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        existing = await self.user_repository.by_email(normalized_email)
        if existing is not None:
            raise UserAlreadyExistsError("Email ya registrado")
        user = User(
            id=IdGenerator.generate("user"),
            email=normalized_email,
            hashed_password=self.password_hasher.hash(password),
            created_at=datetime.now(UTC),
        )
        await self.user_repository.create(user)
        await self.audit_sink.record(
            AuditEvent(
                event_type="auth.register",
                outcome=AuditOutcome.SUCCESS,
                occurred_at=datetime.now(UTC),
                actor_id=user.id,
                actor_email=normalized_email,
            )
        )
        record_auth_event("register_success", user_id=user.id)
        return user
