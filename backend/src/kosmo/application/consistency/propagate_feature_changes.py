from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from kosmo.application.consistency.propagate_discovery_changes import PhasePropagationInfo
from kosmo.contracts import ChatRepository, ConsistencyEvaluationOutput, ConsistencyEvaluator, PlanCambio
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import PlanChangeId, ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)

_log = structlog.get_logger(__name__)

_PHASE_TO_API: dict[SpecPhase, str] = {
    SpecPhase.DESCUBRIMIENTO: "discovery",
    SpecPhase.CARACTERISTICAS: "features",
    SpecPhase.REQUISITOS: "requirements",
    SpecPhase.MODELO: "model",
}


@dataclass(frozen=True)
class PropagateFeatureChangesInput:
    project_id: ProjectId
    phase: SpecPhase
    applied_change_ids: list[PlanChangeId]


@dataclass(frozen=True)
class PropagateFeatureChangesOutput:
    affected_phases: list[PhasePropagationInfo] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


class PropagateFeatureChangesUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        diagram_repo: ActivityDiagramRepository,
        chat_repo: ChatRepository,
        consistency_evaluator: ConsistencyEvaluator,
        traceability_repo: object | None = None,
    ) -> None:
        self._project_repo = project_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._diagram_repo = diagram_repo
        self._chat_repo = chat_repo
        self._consistency_evaluator = consistency_evaluator
        self._traceability_repo = traceability_repo

    async def execute(self, input_data: PropagateFeatureChangesInput) -> PropagateFeatureChangesOutput:
        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/plan/apply",
            )

        applied_changes = await self._load_applied_changes(
            input_data.project_id, input_data.phase, input_data.applied_change_ids
        )

        affected_phases: list[PhasePropagationInfo] = []

        # 1. Upstream: Descubrimiento
        discovery_info = await self._evaluate_discovery(input_data.project_id, applied_changes)
        if discovery_info.affected_count > 0:
            affected_phases.append(discovery_info)

        # 2. Downstream: Requisitos
        req_info = await self._evaluate_requirements(input_data.project_id, applied_changes)
        if req_info.affected_count > 0:
            affected_phases.append(req_info)

        # 3. Downstream: Modelo del Producto
        model_info = await self._evaluate_model(input_data.project_id, applied_changes)
        if model_info.affected_count > 0:
            affected_phases.append(model_info)

        return PropagateFeatureChangesOutput(affected_phases=affected_phases)

    async def _load_applied_changes(
        self, project_id: ProjectId, phase: SpecPhase, change_ids: list[PlanChangeId]
    ) -> list[PlanCambio]:
        all_changes = await self._chat_repo.list_plan_changes(project_id, phase)
        by_id = {c.id: c for c in all_changes}
        return [by_id[cid] for cid in change_ids if cid in by_id]

    async def _evaluate_discovery(
        self, project_id: ProjectId, applied_changes: list[PlanCambio]
    ) -> PhasePropagationInfo:
        try:
            result: ConsistencyEvaluationOutput = await self._consistency_evaluator.evaluate(
                source_phase=SpecPhase.CARACTERISTICAS,
                target_phase=SpecPhase.DESCUBRIMIENTO,
                project_id=project_id,
                applied_changes=applied_changes,
            )
        except Exception:
            _log.warning(
                "propagate_feature.evaluate_discovery_failed",
                project_id=str(project_id),
                exc_info=True,
            )
            return PhasePropagationInfo(
                phase=_PHASE_TO_API[SpecPhase.DESCUBRIMIENTO],
                affected_count=0,
                affected_ids=[],
            )

        return PhasePropagationInfo(
            phase=_PHASE_TO_API[SpecPhase.DESCUBRIMIENTO],
            affected_count=len(result.affected_artifact_ids),
            affected_ids=result.affected_artifact_ids,
        )

    async def _evaluate_requirements(
        self, project_id: ProjectId, applied_changes: list[PlanCambio]
    ) -> PhasePropagationInfo:
        try:
            result: ConsistencyEvaluationOutput = await self._consistency_evaluator.evaluate(
                source_phase=SpecPhase.CARACTERISTICAS,
                target_phase=SpecPhase.REQUISITOS,
                project_id=project_id,
                applied_changes=applied_changes,
            )
        except Exception:
            _log.warning(
                "propagate_feature.evaluate_requirements_failed",
                project_id=str(project_id),
                exc_info=True,
            )
            return PhasePropagationInfo(
                phase=_PHASE_TO_API[SpecPhase.REQUISITOS],
                affected_count=0,
                affected_ids=[],
            )

        return PhasePropagationInfo(
            phase=_PHASE_TO_API[SpecPhase.REQUISITOS],
            affected_count=len(result.affected_artifact_ids),
            affected_ids=result.affected_artifact_ids,
        )

    async def _evaluate_model(self, project_id: ProjectId, applied_changes: list[PlanCambio]) -> PhasePropagationInfo:
        try:
            result: ConsistencyEvaluationOutput = await self._consistency_evaluator.evaluate(
                source_phase=SpecPhase.CARACTERISTICAS,
                target_phase=SpecPhase.MODELO,
                project_id=project_id,
                applied_changes=applied_changes,
            )
        except Exception:
            _log.warning(
                "propagate_feature.evaluate_model_failed",
                project_id=str(project_id),
                exc_info=True,
            )
            return PhasePropagationInfo(
                phase=_PHASE_TO_API[SpecPhase.MODELO],
                affected_count=0,
                affected_ids=[],
            )

        return PhasePropagationInfo(
            phase=_PHASE_TO_API[SpecPhase.MODELO],
            affected_count=len(result.affected_artifact_ids),
            affected_ids=result.affected_artifact_ids,
        )
