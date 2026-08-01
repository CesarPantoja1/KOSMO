from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from kosmo.contracts import ConsistencyEvaluator
from kosmo.contracts.chat import PlanCambio
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)

_log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ImpactItem:
    phase: str
    artifact_id: str
    artifact_type: str
    artifact_label: str
    section: str
    rationale: str


@dataclass(frozen=True)
class EvaluateProjectConsistencyInput:
    project_id: ProjectId
    source_phase: SpecPhase
    target_phases: list[SpecPhase]
    applied_changes: list[PlanCambio]


@dataclass(frozen=True)
class EvaluateProjectConsistencyOutput:
    report_id: str
    source_phase: str
    upstream_impact: list[ImpactItem] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    downstream_impact: list[ImpactItem] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


class EvaluateProjectConsistencyUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        evaluator: ConsistencyEvaluator,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        diagram_repo: ActivityDiagramRepository,
    ) -> None:
        self._project_repo = project_repo
        self._evaluator = evaluator
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._diagram_repo = diagram_repo

    async def execute(self, input_data: EvaluateProjectConsistencyInput) -> EvaluateProjectConsistencyOutput:
        from ulid import ULID

        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/consistency",
            )

        report_id = f"cnr_{ULID().hex}"
        downstream: list[ImpactItem] = []
        upstream: list[ImpactItem] = []

        for target_spec in input_data.target_phases:
            api_phase = _SPEC_TO_API.get(target_spec, target_spec.value)

            try:
                result = await self._evaluator.evaluate(
                    source_phase=input_data.source_phase,
                    target_phase=target_spec,
                    project_id=input_data.project_id,
                    applied_changes=input_data.applied_changes,
                )
            except Exception:
                _log.warning(
                    "consistency.evaluate_failed",
                    project_id=str(input_data.project_id),
                    source=input_data.source_phase,
                    target=target_spec,
                    exc_info=True,
                )
                continue

            items = await self._enrich_affected(result.affected_artifact_ids, api_phase, target_spec)

            if _is_upstream(api_phase, input_data.source_phase.value):
                upstream.extend(items)
            else:
                downstream.extend(items)

        return EvaluateProjectConsistencyOutput(
            report_id=report_id,
            source_phase=input_data.source_phase.value,
            upstream_impact=upstream,
            downstream_impact=downstream,
        )

    async def _enrich_affected(
        self, artifact_ids: list[str], api_phase: str, target_spec: SpecPhase
    ) -> list[ImpactItem]:
        items: list[ImpactItem] = []

        if target_spec not in {SpecPhase.CARACTERISTICAS, SpecPhase.REQUISITOS, SpecPhase.MODELO}:
            return items

        for fid_str in artifact_ids:
            feature = await self._feature_repo.by_id(FeatureId(fid_str))
            if feature is None:
                continue

            if target_spec == SpecPhase.CARACTERISTICAS:
                items.append(
                    ImpactItem(
                        phase=api_phase,
                        artifact_id=fid_str,
                        artifact_type="Feature",
                        artifact_label=feature.display_id,
                        section="title",
                        rationale="El cambio en Descubrimiento afecta esta característica.",
                    )
                )
            elif target_spec == SpecPhase.REQUISITOS:
                req_md = await self._requirement_repo.by_feature_id(feature.id)
                if req_md is not None:
                    items.append(
                        ImpactItem(
                            phase=api_phase,
                            artifact_id=fid_str,
                            artifact_type="EARSRequirement",
                            artifact_label=f"REQ-{feature.display_id}",
                            section="estructura EARS",
                            rationale="El cambio en Descubrimiento afecta los requisitos de esta característica.",
                        )
                    )
            elif target_spec == SpecPhase.MODELO:
                exists = await self._diagram_repo.exists(feature.id)
                if exists:
                    items.append(
                        ImpactItem(
                            phase=api_phase,
                            artifact_id=fid_str,
                            artifact_type="ActivityDiagram",
                            artifact_label=feature.display_id,
                            section="estructura UML",
                            rationale="El cambio podría requerir actualizar el diagrama de actividad.",
                        )
                    )

        return items


_SPEC_TO_API: dict[SpecPhase, str] = {
    SpecPhase.DESCUBRIMIENTO: "discovery",
    SpecPhase.CARACTERISTICAS: "features",
    SpecPhase.REQUISITOS: "requirements",
    SpecPhase.MODELO: "model",
}


def _is_upstream(api_phase: str, source_api: str) -> bool:
    order = ["discovery", "features", "requirements", "model"]
    try:
        return order.index(api_phase) < order.index(source_api)
    except ValueError:
        return False
