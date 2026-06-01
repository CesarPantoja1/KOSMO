from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from kosmo.contracts.sdd.constitution import Constitution
from kosmo.contracts.sdd.discovery import DiscoveryDocument, ProjectRoadmap
from kosmo.contracts.sdd.domain_model import DomainModel
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ProjectId, SpecId, UserId
from kosmo.contracts.sdd.tasks import Task


class SpecPhase(StrEnum):
    DESCUBRIMIENTO = "descubrimiento"
    CARACTERISTICAS = "caracteristicas"
    REQUISITOS = "requisitos"
    MODELO = "modelo"
    PROTOTIPO = "prototipo"
    IMPLEMENTACION = "implementacion"


class SpecDocument(BaseModel):
    id: SpecId
    project_id: ProjectId
    discovery: DiscoveryDocument | None = None
    roadmap: ProjectRoadmap | None = None
    features: list[Feature] = []
    requirements: list[EARSRequirement] = []
    design: DomainModel | None = None
    tasks: list[Task] = []
    phase: SpecPhase = SpecPhase.DESCUBRIMIENTO
    created_by: UserId | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    constitution: Constitution | None = None
