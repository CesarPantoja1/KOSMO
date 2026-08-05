from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from kosmo.application.consistency.propagate_discovery_changes import PhasePropagationInfo
from kosmo.contracts import ChatRepository, ConsistencyEvaluator
from kosmo.contracts.chat import PlanCambio
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, PlanChangeId, ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    FeatureRepository,
    ProjectRepository,
)

_log = structlog.get_logger(__name__)

_PHASE_TO_API: dict[SpecPhase, str] = {
    SpecPhase.DESCUBRIMIENTO: "discovery",
    SpecPhase.CARACTERISTICAS: "features",
    SpecPhase.REQUISITOS: "requirements",
    SpecPhase.MODELO: "model",
}


@dataclass(frozen=True)
class PropagateRequirementChangesInput:
    project_id: ProjectId
    feature_id: FeatureId
    applied_change_ids: list[PlanChangeId]


@dataclass(frozen=True)
class PropagateRequirementChangesOutput:
    affected_phases: list[PhasePropagationInfo] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


class PropagateRequirementChangesUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        feature_repo: FeatureRepository,
        diagram_repo: ActivityDiagramRepository,
        chat_repo: ChatRepository,
        consistency_evaluator: ConsistencyEvaluator,
    ) -> None:
        self._project_repo = project_repo
        self._feature_repo = feature_repo
        self._diagram_repo = diagram_repo
        self._chat_repo = chat_repo
        self._consistency_evaluator = consistency_evaluator

    async def execute(self, input_data: PropagateRequirementChangesInput) -> PropagateRequirementChangesOutput:
        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/plan/apply",
            )

        applied_changes = await self._load_applied_changes(input_data.project_id, input_data.applied_change_ids)

        affected_phases: list[PhasePropagationInfo] = []

        upstream_feat = await self._evaluate_upstream(input_data.project_id, applied_changes, SpecPhase.CARACTERISTICAS)
        if upstream_feat.affected_count > 0:
            affected_phases.append(upstream_feat)

        upstream_disc = await self._evaluate_upstream(input_data.project_id, applied_changes, SpecPhase.DESCUBRIMIENTO)
        if upstream_disc.affected_count > 0:
            affected_phases.append(upstream_disc)

        downstream_model = await self._evaluate_model(input_data.feature_id)
        if downstream_model.affected_count > 0:
            affected_phases.append(downstream_model)

        return PropagateRequirementChangesOutput(affected_phases=affected_phases)

    async def _load_applied_changes(self, project_id: ProjectId, change_ids: list[PlanChangeId]) -> list[PlanCambio]:
        if not change_ids:
            return []
        all_changes = await self._chat_repo.list_plan_changes(project_id, SpecPhase.REQUISITOS)
        by_id: dict[PlanChangeId, PlanCambio] = {c.id: c for c in all_changes}
        return [by_id[cid] for cid in change_ids if cid in by_id]

    async def _evaluate_upstream(
        self, project_id: ProjectId, applied_changes: list[PlanCambio], target_phase: SpecPhase
    ) -> PhasePropagationInfo:
        try:
            result = await self._consistency_evaluator.evaluate(
                source_phase=SpecPhase.REQUISITOS,
                target_phase=target_phase,
                project_id=project_id,
                applied_changes=applied_changes,
            )
        except Exception:
            _log.warning(
                "propagate.evaluate_upstream_failed",
                project_id=str(project_id),
                phase=target_phase.value,
                exc_info=True,
            )
            return PhasePropagationInfo(
                phase=_PHASE_TO_API[target_phase],
                affected_count=0,
                affected_ids=[],
            )

        return PhasePropagationInfo(
            phase=_PHASE_TO_API[target_phase],
            affected_count=len(result.affected_artifact_ids),
            affected_ids=result.affected_artifact_ids,
        )

    async def _evaluate_model(self, feature_id: FeatureId) -> PhasePropagationInfo:
        diagram_exists = await self._diagram_repo.exists(feature_id)
        if not diagram_exists:
            return PhasePropagationInfo(
                phase=_PHASE_TO_API[SpecPhase.MODELO],
                affected_count=0,
                affected_ids=[],
            )
        return PhasePropagationInfo(
            phase=_PHASE_TO_API[SpecPhase.MODELO],
            affected_count=1,
            affected_ids=[str(feature_id)],
        )
