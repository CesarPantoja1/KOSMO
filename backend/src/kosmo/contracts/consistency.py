from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from kosmo.contracts.chat import DiffCambio, PlanCambio
from kosmo.contracts.sdd.document import SpecPhase


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
