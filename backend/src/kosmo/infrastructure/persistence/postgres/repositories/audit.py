from uuid import UUID, uuid4

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.audit import AuditEvent
from kosmo.infrastructure.persistence.postgres.models import AuditEventModel

_logger = structlog.get_logger("kosmo.audit")


def _coerce_uuid(value: str | None) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


class SqlAlchemyAuditEventSink:
    """Persiste eventos de auditoría en `audit_log`.

    Best-effort: cualquier `SQLAlchemyError` se registra como warning y se
    descarta. El log de auditoría nunca debe romper el flujo de negocio,
    aunque la pérdida de un evento queda visible en los logs estructurados
    para alerting externo.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record(self, event: AuditEvent) -> None:
        ctx = structlog.contextvars.get_contextvars()
        request_id = ctx.get("request_id")
        ip_address = ctx.get("ip_address")
        user_agent = ctx.get("user_agent")

        row = AuditEventModel(
            id=uuid4(),
            created_at=event.occurred_at,
            event_type=event.event_type,
            outcome=event.outcome.value,
            actor_id=_coerce_uuid(event.actor_id),
            actor_email=event.actor_email,
            ip_address=str(ip_address) if ip_address else None,
            user_agent=str(user_agent) if user_agent else None,
            request_id=str(request_id) if request_id else None,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            payload=dict(event.metadata),
        )
        try:
            async with self._session_factory() as session:
                session.add(row)
                await session.commit()
        except SQLAlchemyError as exc:
            _logger.warning(
                "audit.persist_failed",
                event_type=event.event_type,
                outcome=event.outcome.value,
                error=str(exc),
            )
