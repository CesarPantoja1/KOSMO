from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from kosmo.contracts.sdd.ids import ProjectId, UserId


class ProjectStatus(StrEnum):
    EN_PROGRESO = "en_progreso"
    FINALIZADO = "finalizado"


class ProjectPhase(StrEnum):
    DESCUBRIMIENTO = "descubrimiento"
    CARACTERISTICAS = "caracteristicas"
    REQUISITOS = "requisitos"
    MODELO = "modelo"
    IMPLEMENTACION = "implementacion"


class Project(BaseModel):
    id: ProjectId
    name: str
    slug: str = ""
    description: str
    current_phase: ProjectPhase = ProjectPhase.DESCUBRIMIENTO
    status: ProjectStatus = ProjectStatus.EN_PROGRESO
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: UserId | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    discovery_document: dict[str, Any] | None = None
