from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field
from ulid import ULID

from kosmo.contracts.chat import DiffCambio, PlanCambio
from kosmo.contracts.consistency import ConsistencyEvaluator, ConsistencyStatus
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, PlanChangeId, ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository


class CheckFeatureConsistencyInput(BaseModel):
    project_id: ProjectId
    feature_id: FeatureId
    title: str = Field(..., max_length=50)
    description: str = Field(..., max_length=500)


@dataclass(frozen=True)
class CheckFeatureConsistencyOutput:
    is_consistent: bool
    reason: str | None = None
    conflicting_section: str | None = None


class CheckFeatureConsistencyUseCase:
    def __init__(
        self,
        feature_repo: FeatureRepository,
        consistency_evaluator: ConsistencyEvaluator,
    ) -> None:
        self._feature_repo = feature_repo
        self._consistency_evaluator = consistency_evaluator

    async def execute(self, input_dto: CheckFeatureConsistencyInput) -> CheckFeatureConsistencyOutput:
        feature = await self._feature_repo.by_id(input_dto.feature_id)
        if feature is None or feature.project_id != input_dto.project_id:
            raise FeatureNotFoundError(feature_id=str(input_dto.feature_id))

        plan_cambio = PlanCambio(
            id=PlanChangeId(ULID().hex),
            section=f"Característica {feature.number}",
            description="Edición manual de característica",
            diff=DiffCambio(
                before=f"Título: {feature.title}\nDescripción: {feature.description}",
                after=f"Título: {input_dto.title}\nDescripción: {input_dto.description}",
            ),
        )

        consistency_output = await self._consistency_evaluator.evaluate(
            source_phase=SpecPhase.CARACTERISTICAS,
            target_phase=SpecPhase.DESCUBRIMIENTO,
            project_id=input_dto.project_id,
            applied_changes=[plan_cambio],
        )

        if consistency_output.status == ConsistencyStatus.ANALIZADO_CON_IMPACTO:
            for action in consistency_output.actions:
                if action.action == "update":
                    return CheckFeatureConsistencyOutput(
                        is_consistent=False,
                        reason=action.rationale,
                        conflicting_section=action.suggested_field or None,
                    )

            if consistency_output.rationale:
                return CheckFeatureConsistencyOutput(
                    is_consistent=False,
                    reason=consistency_output.rationale,
                )

        return CheckFeatureConsistencyOutput(is_consistent=True)
