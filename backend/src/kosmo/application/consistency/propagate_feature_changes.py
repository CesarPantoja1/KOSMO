from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from kosmo.application.consistency.propagate_discovery_changes import PhasePropagationInfo
from kosmo.contracts import ChatRepository, ConsistencyEvaluationOutput, ConsistencyEvaluator, PlanCambio
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import PlanChangeId, ProjectId
from kosmo.contracts import ChatRepository, ConsistencyEvaluator
from kosmo.contracts.chat import PlanCambio
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, PlanChangeId, ProjectId
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
    feature_id: FeatureId
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
            input_data.project_id, input_data.applied_change_ids
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
        upstream = await self._evaluate_upstream(input_data.project_id, applied_changes)
        if upstream.affected_count > 0:
            affected_phases.append(upstream)

        downstream_req = await self._evaluate_requirements(input_data.feature_id)
        if downstream_req.affected_count > 0:
            affected_phases.append(downstream_req)

        downstream_model = await self._evaluate_model(input_data.feature_id)
        if downstream_model.affected_count > 0:
            affected_phases.append(downstream_model)

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
        self, project_id: ProjectId, change_ids: list[PlanChangeId]
    ) -> list[PlanCambio]:
        from kosmo.contracts.chat import PlanCambio as _PC

        if not change_ids:
            return []
        all_changes = await self._chat_repo.list_plan_changes(project_id, SpecPhase.CARACTERISTICAS)
        by_id: dict[PlanChangeId, _PC] = {c.id: c for c in all_changes}
        return [by_id[cid] for cid in change_ids if cid in by_id]

    async def _evaluate_upstream(
        self, project_id: ProjectId, applied_changes: list[PlanCambio]
    ) -> PhasePropagationInfo:
        try:
            result = await self._consistency_evaluator.evaluate(
                source_phase=SpecPhase.CARACTERISTICAS,
                target_phase=SpecPhase.DESCUBRIMIENTO,
                project_id=project_id,
                applied_changes=applied_changes,
            )
        except Exception:
            _log.warning(
                "propagate_feature.evaluate_discovery_failed",
                project_id=str(project_id),
                "propagate.evaluate_upstream_failed",
                project_id=str(project_id),
                phase="descubrimiento",
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
    async def _evaluate_requirements(self, feature_id: FeatureId) -> PhasePropagationInfo:
        requirements = await self._requirement_repo.by_feature_id(feature_id)
        if requirements is None:
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
            phase=_PHASE_TO_API[SpecPhase.REQUISITOS],
            affected_count=1,
            affected_ids=[str(feature_id)],
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
            affected_count=len(result.affected_artifact_ids),
            affected_ids=result.affected_artifact_ids,
        return PhasePropagationInfo(
            phase=_PHASE_TO_API[SpecPhase.MODELO],
            affected_count=1,
            affected_ids=[str(feature_id)],
        )
