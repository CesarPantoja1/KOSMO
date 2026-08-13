from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from kosmo.contracts import ChatRepository, ConsistencyEvaluator
from kosmo.contracts.chat import PlanCambio
from kosmo.contracts.consistency import DOWNSTREAM_TARGETS, PhasePropagationInfo
from kosmo.contracts.sdd.document import SPEC_TO_API_PHASE, SpecPhase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, PlanChangeId, ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)

_log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class PropagateChangesInput:
    project_id: ProjectId
    source_phase: SpecPhase
    applied_change_ids: list[PlanChangeId]
    feature_id: FeatureId | None = None


@dataclass(frozen=True)
class PropagateChangesOutput:
    affected_phases: list[PhasePropagationInfo] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


class PropagateChangesUseCase:
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

    async def execute(self, input_data: PropagateChangesInput) -> PropagateChangesOutput:
        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/plan/apply",
            )

        applied_changes = await self._load_applied_changes(
            input_data.project_id, input_data.source_phase, input_data.applied_change_ids
        )

        targets = DOWNSTREAM_TARGETS.get(input_data.source_phase, [])
        affected_phases: list[PhasePropagationInfo] = []

        for target_spec in targets:
            if target_spec == input_data.source_phase:
                continue
            info = await self._evaluate_pair(
                input_data.source_phase, target_spec, input_data.project_id, applied_changes
            )
            if info.affected_count > 0:
                affected_phases.append(info)

        return PropagateChangesOutput(affected_phases=affected_phases)

    async def _load_applied_changes(
        self, project_id: ProjectId, phase: SpecPhase, change_ids: list[PlanChangeId]
    ) -> list[PlanCambio]:
        if not change_ids:
            return []
        all_changes = await self._chat_repo.list_plan_changes(project_id, phase)
        by_id: dict[PlanChangeId, PlanCambio] = {c.id: c for c in all_changes}
        return [by_id[cid] for cid in change_ids if cid in by_id]

    async def _evaluate_pair(
        self,
        source_phase: SpecPhase,
        target_phase: SpecPhase,
        project_id: ProjectId,
        applied_changes: list[PlanCambio],
    ) -> PhasePropagationInfo:
        api_phase = SPEC_TO_API_PHASE[target_phase]
        try:
            result = await self._consistency_evaluator.evaluate(
                source_phase=source_phase,
                target_phase=target_phase,
                project_id=project_id,
                applied_changes=applied_changes,
            )
        except Exception:
            _log.warning(
                "propagate.evaluate_pair_failed",
                project_id=str(project_id),
                source=source_phase.value,
                target=target_phase.value,
                exc_info=True,
            )
            return PhasePropagationInfo(phase=api_phase, affected_count=0, affected_ids=[])

        return PhasePropagationInfo(
            phase=api_phase,
            affected_count=len(result.affected_artifact_ids),
            affected_ids=result.affected_artifact_ids,
        )
