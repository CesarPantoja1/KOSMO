from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from kosmo.contracts.chat import DiffCambio, PlanCambio
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, RequirementId


class TraceabilityRepository(Protocol):
    async def get_impact(self, artifact_id: str) -> dict[str, list[dict[str, str]]]: ...
    async def add_edge(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        origin: str = "llm",
    ) -> None: ...
    async def add_feature_requirement_edges(
        self, feature_id: FeatureId, requirement_ids: list[RequirementId]
    ) -> None: ...
    async def delete_by_entity_id(self, entity_id: str) -> None: ...


class ConsistencyStatus(StrEnum):
    ANALIZADO_SIN_IMPACTO = "analizado_sin_impacto"
    ANALIZADO_CON_IMPACTO = "analizado_con_impacto"
    ANALISIS_FALLIDO = "analisis_fallido"


# Trazabilidad solo hacia la derecha: Descubrimiento -> Caracteristicas -> Requisitos -> Modelo
DOWNSTREAM_TARGETS: dict[SpecPhase, list[SpecPhase]] = {
    SpecPhase.DESCUBRIMIENTO: [SpecPhase.CARACTERISTICAS, SpecPhase.REQUISITOS, SpecPhase.MODELO],
    SpecPhase.CARACTERISTICAS: [SpecPhase.REQUISITOS, SpecPhase.MODELO],
    SpecPhase.REQUISITOS: [SpecPhase.MODELO],
    SpecPhase.MODELO: [],
}

PHASE_ORDER: dict[SpecPhase, int] = {
    SpecPhase.DESCUBRIMIENTO: 0,
    SpecPhase.CARACTERISTICAS: 1,
    SpecPhase.REQUISITOS: 2,
    SpecPhase.MODELO: 3,
}


@dataclass(frozen=True)
class ArtefactoAfectado:
    artifact_id: str
    artifact_type: str
    title: str
    traceability_description: str
    suggested_diff: DiffCambio
    rationale: str | None = None


@dataclass(frozen=True)
class ReporteConsistencia:
    id: str
    source_phase: SpecPhase
    target_phase: SpecPhase
    user_changes: list[PlanCambio] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    affected_artifacts: list[ArtefactoAfectado] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class ArtifactAction:
    artifact_id: str
    action: str  # "update", "delete", "keep"
    rationale: str
    suggested_field: str = ""
    suggested_before: str = ""
    suggested_after: str = ""


@dataclass(frozen=True)
class ImpactItem:
    id: str
    phase: str
    target_id: str
    artifact_type: str
    target_display_id: str
    target_title: str
    section: str
    rationale: str
    diff: dict[str, object] | None = None
    action: str = "update"


@dataclass(frozen=True)
class ConsistencyEvaluationOutput:
    report_id: str
    status: ConsistencyStatus = ConsistencyStatus.ANALIZADO_SIN_IMPACTO
    affected_artifact_ids: list[str] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    rationale: str = ""
    failure_reason: str = ""
    actions: list[ArtifactAction] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    upstream_impact: list[ImpactItem] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    downstream_impact: list[ImpactItem] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


class ConsistencyEvaluator(Protocol):
    async def evaluate(
        self,
        *,
        source_phase: SpecPhase,
        target_phase: SpecPhase,
        project_id: ProjectId,
        applied_changes: list[PlanCambio],
    ) -> ConsistencyEvaluationOutput: ...


@dataclass(frozen=True)
class PhasePropagationInfo:
    phase: str
    affected_count: int
    affected_ids: list[str]
