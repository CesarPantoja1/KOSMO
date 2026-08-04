from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

import structlog
from ulid import ULID

from kosmo.contracts import ConsistencyEvaluator
from kosmo.contracts.chat import PlanCambio
from kosmo.contracts.consistency import ArtifactAction, ConsistencyEvaluationOutput, ConsistencyStatus
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

_ImpactItemDict = dict[str, object]
_ImpactList = list[_ImpactItemDict]

_FULL_CASCADE = [SpecPhase.CARACTERISTICAS, SpecPhase.REQUISITOS, SpecPhase.MODELO]

_PHASE_API: dict[SpecPhase, str] = {
    SpecPhase.CARACTERISTICAS: "features",
    SpecPhase.REQUISITOS: "requirements",
    SpecPhase.MODELO: "model",
}


@dataclass(frozen=True)
class CascadingConsistencyOutput:
    report_id: str
    source_type: str
    source_id: str
    downstream_impact: _ImpactList = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    your_changes: _ImpactList = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


class CascadingConsistencyUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        diagram_repo: ActivityDiagramRepository,
        evaluator: ConsistencyEvaluator,
        traceability_repo: object | None = None,
    ) -> None:
        self._project_repo = project_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._diagram_repo = diagram_repo
        self._evaluator = evaluator
        self._traceability_repo = traceability_repo

    async def execute(
        self,
        project_id: ProjectId,
        source_phase: SpecPhase,
        applied_changes: list[PlanCambio],
    ) -> CascadingConsistencyOutput:
        report_id = f"cnr_{ULID().hex}"
        project = await self._project_repo.by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(project_id),
                instance=f"/api/v1/projects/{project_id}/consistency",
            )

        source_api = _PHASE_API.get(source_phase, source_phase.value)
        downstream: _ImpactList = []

        for target_spec in _FULL_CASCADE:
            try:
                result = await self._evaluator.evaluate(
                    source_phase=source_phase,
                    target_phase=target_spec,
                    project_id=project_id,
                    applied_changes=applied_changes,
                )
            except Exception:
                _log.warning(
                    "cascade.evaluate_failed",
                    project_id=str(project_id),
                    target=target_spec.value,
                    exc_info=True,
                )
                continue

            if not result.affected_artifact_ids:
                continue

            phase_api = _PHASE_API[target_spec]
            items = await _enrich_impact_items(
                result,
                phase_api,
                target_spec,
                self._feature_repo,
                self._requirement_repo,
                self._diagram_repo,
            )
            downstream.extend(items)

        your_changes: list[dict[str, object]] = [
            {
                "change_id": str(c.id),
                "section": c.section,
                "description": c.description,
                "diff": {"before": c.diff.before, "after": c.diff.after},
                "accepted": True,
            }
            for c in applied_changes
        ]

        return CascadingConsistencyOutput(
            report_id=report_id,
            source_type=source_api,
            source_id=str(project_id),
            downstream_impact=downstream,
            your_changes=your_changes,  # type: ignore[reportArgumentType]
        )

    async def execute_stream(
        self,
        project_id: ProjectId,
        source_phase: SpecPhase,
        applied_changes: list[PlanCambio],
    ) -> AsyncGenerator[str]:
        report_id = f"cnr_{ULID().hex}"
        project = await self._project_repo.by_id(project_id)
        if project is None:
            error_event = json.dumps({"type": "error", "message": "Proyecto no encontrado"}, ensure_ascii=False)
            yield f"data: {error_event}\n\n"
            return

        source_api = _PHASE_API.get(source_phase, source_phase.value)
        all_downstream: _ImpactList = []

        for target_spec in _FULL_CASCADE:
            phase_api = _PHASE_API[target_spec]
            phase_label = _phase_label(target_spec)

            yield _sse_event(
                "progress",
                phase=phase_api,
                status="evaluating",
                message=f"Evaluando impacto en {phase_label}...",
            )

            try:
                result = await self._evaluator.evaluate(
                    source_phase=source_phase,
                    target_phase=target_spec,
                    project_id=project_id,
                    applied_changes=applied_changes,
                )
            except Exception:
                _log.warning(
                    "cascade.evaluate_failed",
                    project_id=str(project_id),
                    target=target_spec.value,
                    exc_info=True,
                )
                yield _sse_event(
                    "progress",
                    phase=phase_api,
                    status="error",
                    message=f"No se pudo evaluar {phase_label}",
                )
                continue

            if not result.affected_artifact_ids:
                if result.status == ConsistencyStatus.ANALISIS_FALLIDO:
                    yield _sse_event(
                        "phase_result",
                        phase=phase_api,
                        affected_count=0,
                        status="failed",
                        message=f"El analisis de impacto fallo para {phase_label}",
                    )
                else:
                    yield _sse_event(
                        "phase_result",
                        phase=phase_api,
                        affected_count=0,
                        status="no_impact",
                        message=f"Sin cambios detectados en {phase_label}",
                    )
                continue

            items = await _enrich_impact_items(
                result,
                phase_api,
                target_spec,
                self._feature_repo,
                self._requirement_repo,
                self._diagram_repo,
            )
            all_downstream.extend(items)

            yield _sse_event(
                "phase_result",
                phase=phase_api,
                affected_count=len(items),
                impact=items,
                message=f"{len(items)} artefacto(s) afectado(s) en {phase_label}",
            )

        your_changes: list[dict[str, object]] = [
            {
                "change_id": str(c.id),
                "section": c.section,
                "description": c.description,
                "diff": {"before": c.diff.before, "after": c.diff.after},
                "accepted": True,
            }
            for c in applied_changes
        ]

        complete_event = json.dumps(
            {
                "type": "complete",
                "report": {
                    "report_id": report_id,
                    "source_type": source_api,
                    "source_id": str(project_id),
                    "your_changes": your_changes,
                    "downstream_impact": all_downstream,
                },
            },
            ensure_ascii=False,
        )
        yield f"data: {complete_event}\n\n"


async def _enrich_impact_items(
    result: ConsistencyEvaluationOutput,
    api_phase: str,
    target_spec: SpecPhase,
    feature_repo: FeatureRepository,
    requirement_repo: RequirementRepository,
    diagram_repo: ActivityDiagramRepository,
) -> _ImpactList:
    items: _ImpactList = []

    action_by_id: dict[str, ArtifactAction] = {}
    for a in result.actions:
        action_by_id[a.artifact_id] = a

    for fid_str in result.affected_artifact_ids:
        feature = await feature_repo.by_id(FeatureId(fid_str))
        if feature is None:
            continue

        action = action_by_id.get(fid_str)
        per_rationale = action.rationale if action else result.rationale
        per_action = action.action if action else "update"

        diff: object | None = None
        if action and action.suggested_before and action.suggested_after:
            diff = {
                "field": action.suggested_field or "description",
                "before": action.suggested_before,
                "after": action.suggested_after,
            }

        item_id = f"imp_{ULID().hex}"

        if target_spec == SpecPhase.CARACTERISTICAS:
            items.append(
                {
                    "id": item_id,
                    "phase": api_phase,
                    "targetId": fid_str,
                    "artifact_type": "Feature",
                    "targetDisplayId": feature.display_id,
                    "targetTitle": feature.title,
                    "section": action.suggested_field if action else "title",
                    "rationale": per_rationale
                    or (
                        "Esta característica ya no aplica al descubrimiento actual."
                        if per_action == "delete"
                        else "El cambio en Descubrimiento afecta esta característica."
                    ),
                    "diff": diff,
                    "action": per_action,
                }
            )
        elif target_spec == SpecPhase.REQUISITOS:
            req_md = await requirement_repo.by_feature_id(feature.id)
            if req_md is None:
                continue

            current_reqs = parse_requirements_markdown(req_md, feature.id, feature.number)

            if action and action.suggested_before and action.suggested_after:
                before_reqs = parse_requirements_markdown(
                    action.suggested_before, feature.id, feature.number
                )
                after_reqs = parse_requirements_markdown(
                    action.suggested_after, feature.id, feature.number
                )
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
                    per_diff = {
                        "field": "statement",
                        "before": before_req.statement,
                        "after": after_req.statement,
                    }
                    per_action = "update"
                elif before_req and not after_req:
                    per_diff = None
                    per_action = "delete" if per_action == "delete" else "update"
                elif not before_req and after_req:
                    per_diff = {
                        "field": "statement",
                        "before": "",
                        "after": after_req.statement,
                    }
                    per_action = "create"
                else:
                    per_diff = None
                    per_action = per_action

                target_req = before_req or after_req
                req_title = target_req.title if target_req else req_display_id
                items.append(
                    {
                        "id": f"imp_{ULID().hex}",
                        "phase": api_phase,
                        "targetId": fid_str,
                        "artifact_type": "EARSRequirement",
                        "targetDisplayId": req_display_id,
                        "targetTitle": req_title,
                        "section": "statement",
                        "rationale": per_rationale
                        or (
                            "Se eliminará en cascada al eliminar la característica."
                            if per_action == "delete"
                            else "El cambio en Descubrimiento afecta este requisito."
                        ),
                        "diff": per_diff,
                        "action": per_action,
                    }
                )
        elif target_spec == SpecPhase.MODELO:
            exists = await diagram_repo.exists(feature.id)
            if exists:
                items.append(
                    {
                        "id": item_id,
                        "phase": api_phase,
                        "targetId": fid_str,
                        "artifact_type": "ActivityDiagram",
                        "targetDisplayId": feature.display_id,
                        "targetTitle": f"Diagrama de {feature.title}",
                        "section": action.suggested_field if action else "estructura UML",
                        "rationale": per_rationale or "El cambio podría requerir actualizar el diagrama de actividad.",
                        "diff": diff,
                        "action": per_action,
                    }
                )

    return items


def _sse_event(event_type: str, **kwargs: object) -> str:
    payload: dict[str, object] = {"type": event_type, **kwargs}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _phase_label(spec: SpecPhase) -> str:
    labels = {
        SpecPhase.CARACTERISTICAS: "Características",
        SpecPhase.REQUISITOS: "Requisitos",
        SpecPhase.MODELO: "Modelo",
    }
    return labels.get(spec, spec.value)
