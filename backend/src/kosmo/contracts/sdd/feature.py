from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.requirements_document import RequirementsDocument


class FeatureStatus(StrEnum):
    BORRADOR = "borrador"
    APROBADA = "aprobada"


class Feature(BaseModel):
    id: FeatureId
    project_id: ProjectId
    title: str
    slug: str = ""
    description: str
    status: FeatureStatus = FeatureStatus.BORRADOR
    requirements: RequirementsDocument | None = None
    requirements_document: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
