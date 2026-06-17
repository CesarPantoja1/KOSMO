"""Puertos del bounded context de auditoría."""

from typing import Protocol

from kosmo.contracts.audit.events import AuditEvent


class AuditEventSink(Protocol):
    async def record(self, event: AuditEvent) -> None: ...
