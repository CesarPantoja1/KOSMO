from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from kosmo.contracts import ArtifactAction, ConsistencyEvaluationOutput, ConsistencyEvaluator, ImpactItem
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
from kosmo.domain.sdd.requirements_markdown import parse_requirements_markdown

_log = structlog.get_logger(__name__)


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

            try:
                items = await self._enrich_affected(result, api_phase, target_spec)
            except Exception:
                _log.warning(
                    "consistency.enrich_failed",
                    project_id=str(input_data.project_id),
                    target=target_spec,
                    exc_info=True,
                )
                continue

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
        self, result: ConsistencyEvaluationOutput, api_phase: str, target_spec: SpecPhase
    ) -> list[ImpactItem]:
        from ulid import ULID

        items: list[ImpactItem] = []

        if target_spec not in {SpecPhase.CARACTERISTICAS, SpecPhase.REQUISITOS, SpecPhase.MODELO}:
            return items

        action_by_id: dict[str, ArtifactAction] = {}
        for a in result.actions:
            action_by_id[a.artifact_id] = a

        artifact_ids = result.affected_artifact_ids

        for fid_str in artifact_ids:
            feature = await self._feature_repo.by_id(FeatureId(fid_str))
            if feature is None:
                continue

            action = action_by_id.get(fid_str)
            per_rationale = action.rationale if action else result.rationale
            per_action = action.action if action else "update"

            diff: dict[str, object] | None = None
            if action and action.suggested_before and action.suggested_after:
                diff = {
                    "field": action.suggested_field or "description",
                    "before": action.suggested_before,
                    "after": action.suggested_after,
                }

            if target_spec == SpecPhase.CARACTERISTICAS:
                items.append(
                    ImpactItem(
                        id=f"imp_{ULID().hex}",
                        phase=api_phase,
                        target_id=fid_str,
                        artifact_type="Feature",
                        target_display_id=feature.display_id,
                        target_title=feature.title,
                        section=action.suggested_field if action else "title",
                        rationale=per_rationale
                        or (
                            "Esta característica ya no aplica al descubrimiento actual."
                            if per_action == "delete"
                            else "El cambio en Descubrimiento afecta esta característica."
                        ),
                        diff=diff,
                        action=per_action,
                    )
                )
            elif target_spec == SpecPhase.REQUISITOS:
                req_md = await self._requirement_repo.by_feature_id(feature.id)
                if req_md is None:
                    continue

                current_reqs = parse_requirements_markdown(req_md, feature.id, feature.number)

                if action and action.suggested_before and action.suggested_after:
                    before_reqs = parse_requirements_markdown(action.suggested_before, feature.id, feature.number)
                    after_reqs = parse_requirements_markdown(action.suggested_after, feature.id, feature.number)
                    before_by_id = {r.display_id: r for r in before_reqs}
                    after_by_id = {r.display_id: r for r in after_reqs}
                    all_ids = sorted(set(before_by_id.keys()) | set(after_by_id.keys()))
                else:
                    before_by_id = {r.display_id: r for r in current_reqs}
                    after_by_id = {}
                    all_ids = sorted(before_by_id.keys())

                for req_display_id in all_ids:
                    before_req = before_by_id.get(req_display_id)
                    after_req = after_by_id.get(req_display_id)

                    if before_req and after_req and before_req.statement != after_req.statement:
                        per_diff: dict[str, object] | None = {
                            "field": "statement",
                            "before": before_req.statement,
                            "after": after_req.statement,
                        }
                        req_action = "update"
                    elif before_req and not after_req:
                        per_diff = None
                        req_action = "delete"
                    elif not before_req and after_req:
                        per_diff = {
                            "field": "statement",
                            "before": "",
                            "after": after_req.statement,
                        }
                        req_action = "create"
                    else:
                        per_diff = None
                        req_action = per_action

                    target_req = before_req or after_req
                    req_title = target_req.title if target_req else req_display_id
                    items.append(
                        ImpactItem(
                            id=f"imp_{ULID().hex}",
                            phase=api_phase,
                            target_id=fid_str,
                            artifact_type="EARSRequirement",
                            target_display_id=req_display_id,
                            target_title=req_title,
                            section="statement",
                            rationale=per_rationale
                            or (
                                "Se eliminará en cascada al eliminar la característica."
                                if req_action == "delete"
                                else "El cambio en Descubrimiento afecta este requisito."
                            ),
                            diff=per_diff,
                            action=req_action,
                        )
                    )
            elif target_spec == SpecPhase.MODELO:
                exists = await self._diagram_repo.exists(feature.id)
                if exists:
                    items.append(
                        ImpactItem(
                            id=f"imp_{ULID().hex}",
                            phase=api_phase,
                            target_id=fid_str,
                            artifact_type="ActivityDiagram",
                            target_display_id=feature.display_id,
                            target_title=f"Diagrama de {feature.title}",
                            section=action.suggested_field if action else "estructura UML",
                            rationale=per_rationale or "El cambio podría requerir actualizar el diagrama de actividad.",
                            diff=diff,
                            action=per_action,
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
