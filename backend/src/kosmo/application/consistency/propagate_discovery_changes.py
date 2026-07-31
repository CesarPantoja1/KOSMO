from __future__ import annotations

from dataclasses import dataclass, field

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

_PHASE_TO_API: dict[SpecPhase, str] = {
    SpecPhase.DESCUBRIMIENTO: "discovery",
    SpecPhase.CARACTERISTICAS: "features",
    SpecPhase.REQUISITOS: "requirements",
    SpecPhase.MODELO: "model",
}

_API_PHASES = {"features", "requirements", "model"}


@dataclass(frozen=True)
class PropagateDiscoveryChangesInput:
    project_id: ProjectId
    phase: SpecPhase
    applied_change_ids: list[PlanChangeId]


@dataclass(frozen=True)
class PhasePropagationInfo:
    phase: str
    affected_count: int
    affected_ids: list[str]


@dataclass(frozen=True)
class PropagateDiscoveryChangesOutput:
    affected_phases: list[PhasePropagationInfo] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


class PropagateDiscoveryChangesUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        diagram_repo: ActivityDiagramRepository,
        chat_repo: ChatRepository,
        consistency_evaluator: ConsistencyEvaluator,
    ) -> None:
        self._project_repo = project_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._diagram_repo = diagram_repo
        self._chat_repo = chat_repo
        self._consistency_evaluator = consistency_evaluator

    async def execute(self, input_data: PropagateDiscoveryChangesInput) -> PropagateDiscoveryChangesOutput:
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

        features_info = await self._evaluate_features(input_data.project_id, applied_changes)
        if features_info.affected_count > 0:
            affected_phases.append(features_info)

        if features_info.affected_ids:
            for feature_id_str in features_info.affected_ids:
                req_info = await self._evaluate_requirements(feature_id_str, input_data.project_id, applied_changes)
                if req_info.affected_count > 0:
                    affected_phases.append(req_info)

                model_info = await self._evaluate_model(feature_id_str, input_data.project_id, applied_changes)
                if model_info.affected_count > 0:
                    affected_phases.append(model_info)

        return PropagateDiscoveryChangesOutput(affected_phases=affected_phases)

    async def _load_applied_changes(
        self, project_id: ProjectId, phase: SpecPhase, change_ids: list[PlanChangeId]
    ) -> list[PlanCambio]:
        all_changes = await self._chat_repo.list_plan_changes(project_id, phase)
        by_id = {c.id: c for c in all_changes}
        return [by_id[cid] for cid in change_ids if cid in by_id]

    async def _evaluate_features(
        self, project_id: ProjectId, applied_changes: list[PlanCambio]
    ) -> PhasePropagationInfo:
        features = await self._feature_repo.list_by_project(project_id)
        if not features:
            return PhasePropagationInfo(
                phase=_PHASE_TO_API[SpecPhase.CARACTERISTICAS], affected_count=0, affected_ids=[]
            )

        try:
            result: ConsistencyEvaluationOutput = await self._consistency_evaluator.evaluate(
                source_phase=SpecPhase.DESCUBRIMIENTO,
                target_phase=SpecPhase.CARACTERISTICAS,
                project_id=project_id,
                applied_changes=applied_changes,
            )
        except Exception:
            return PhasePropagationInfo(
                phase=_PHASE_TO_API[SpecPhase.CARACTERISTICAS],
                affected_count=len(features),
                affected_ids=[str(f.id) for f in features],
            )

        return PhasePropagationInfo(
            phase=_PHASE_TO_API[SpecPhase.CARACTERISTICAS],
            affected_count=len(result.affected_artifact_ids),
            affected_ids=result.affected_artifact_ids,
        )

    async def _evaluate_requirements(
        self, feature_id_str: str, project_id: ProjectId, applied_changes: list[PlanCambio]
    ) -> PhasePropagationInfo:
        from kosmo.contracts.sdd.ids import FeatureId

        feature_id = FeatureId(feature_id_str)
        requirements = await self._requirement_repo.by_feature_id(feature_id)
        if requirements is None:
            return PhasePropagationInfo(phase=_PHASE_TO_API[SpecPhase.REQUISITOS], affected_count=0, affected_ids=[])

        try:
            result = await self._consistency_evaluator.evaluate(
                source_phase=SpecPhase.DESCUBRIMIENTO,
                target_phase=SpecPhase.REQUISITOS,
                project_id=project_id,
                applied_changes=applied_changes,
            )
        except Exception:
            return PhasePropagationInfo(
                phase=_PHASE_TO_API[SpecPhase.REQUISITOS],
                affected_count=1,
                affected_ids=[feature_id_str],
            )

        return PhasePropagationInfo(
            phase=_PHASE_TO_API[SpecPhase.REQUISITOS],
            affected_count=len(result.affected_artifact_ids),
            affected_ids=result.affected_artifact_ids,
        )

    async def _evaluate_model(
        self, feature_id_str: str, project_id: ProjectId, applied_changes: list[PlanCambio]
    ) -> PhasePropagationInfo:
        from kosmo.contracts.sdd.ids import FeatureId

        feature_id = FeatureId(feature_id_str)
        diagram_exists = await self._diagram_repo.exists(feature_id)
        if not diagram_exists:
            return PhasePropagationInfo(phase=_PHASE_TO_API[SpecPhase.MODELO], affected_count=0, affected_ids=[])

        try:
            result = await self._consistency_evaluator.evaluate(
                source_phase=SpecPhase.DESCUBRIMIENTO,
                target_phase=SpecPhase.MODELO,
                project_id=project_id,
                applied_changes=applied_changes,
            )
        except Exception:
            return PhasePropagationInfo(
                phase=_PHASE_TO_API[SpecPhase.MODELO],
                affected_count=1,
                affected_ids=[feature_id_str],
            )

        return PhasePropagationInfo(
            phase=_PHASE_TO_API[SpecPhase.MODELO],
            affected_count=len(result.affected_artifact_ids),
            affected_ids=result.affected_artifact_ids,
        )
