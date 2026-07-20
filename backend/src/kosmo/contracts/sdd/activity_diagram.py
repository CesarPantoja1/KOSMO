from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from kosmo.contracts.sdd.errors import ProblemDetail, SpecError
from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId


@dataclass(frozen=True)
class DiagramaActividad:
    id: ActivityDiagramId
    feature_id: FeatureId
    diagram_syntax: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class DiagramNotFoundError(SpecError):
    def __init__(
        self,
        *,
        feature_id: str,
        instance: str = "/api/v1/features/diagram",
    ) -> None:
        problem = ProblemDetail(
            type="urn:kosmo:diagram:not-found",
            title="Diagrama de actividad no encontrado",
            status=404,
            detail=f"La feature {feature_id} no tiene un diagrama de actividad generado",
            instance=instance,
        )
        super().__init__(problem)
