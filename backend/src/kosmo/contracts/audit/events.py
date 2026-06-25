"""Tipos del bounded context de auditoría.

El registro de auditoría es un log inmutable, append-only, que persiste eventos
relevantes para forensics y cumplimiento. Es independiente de los logs HTTP
(volátiles, en stdout) y de las métricas OTel (agregadas, no individuales).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class AuditOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


def _empty_metadata() -> dict[str, Any]:
    return {}


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_type: str
    outcome: AuditOutcome
    occurred_at: datetime
    actor_id: str | None = None
    actor_email: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=_empty_metadata)
