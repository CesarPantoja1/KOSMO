from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from ulid import ULID

from kosmo.contracts import ConsistencyEvaluator, DiffCambio, PlanCambio
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import PlanChangeId, ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    FeatureRepository,
    RequirementRepository,
)
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.schemas import (
    ChangeInputView,
    ConsistencyReportView,
    EvaluateConsistencyRequestView,
    HttpErrorResponse,
    ImpactItemView,
)

_log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/consistency",
    tags=["consistency"],
    responses={
        401: {"model": HttpErrorResponse, "description": "Token ausente, inválido o expirado"},
        404: {"model": HttpErrorResponse, "description": "Proyecto no encontrado"},
    },
)

_PHASE_TO_API: dict[str, str] = {
    "descubrimiento": "discovery",
    "caracteristicas": "features",
    "requisitos": "requirements",
    "modelo": "model",
}

_DOWNSTREAM_PHASES = ["caracteristicas", "requisitos", "modelo"]


def _consistency_evaluator(request: Request) -> ConsistencyEvaluator:
    return request.app.state.consistency_evaluator


def _feature_repo(request: Request) -> FeatureRepository:
    return request.app.state.feature_repo


def _requirement_repo(request: Request) -> RequirementRepository:
    return request.app.state.requirement_repo


def _diagram_repo(request: Request) -> ActivityDiagramRepository:
    return request.app.state.diagram_repo


def _resolve_origin_phase(phase_name: str) -> SpecPhase:
    reverse = {
        "discovery": SpecPhase.DESCUBRIMIENTO,
        "features": SpecPhase.CARACTERISTICAS,
        "requirements": SpecPhase.REQUISITOS,
    }
    if phase_name not in reverse:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fase de origen desconocida: '{phase_name}'. Valores esperados: discovery, features, requirements.",
        )
    return reverse[phase_name]


def _to_api_phase(spec: SpecPhase) -> str:
    return _PHASE_TO_API.get(spec.value, spec.value)


def _resolve_targets(phase_destination: str | None) -> list[str]:
    if phase_destination:
        return [phase_destination]
    return list(_DOWNSTREAM_PHASES)


def _to_spec_phase(api_phase: str) -> SpecPhase:
    reverse = {
        "discovery": SpecPhase.DESCUBRIMIENTO,
        "features": SpecPhase.CARACTERISTICAS,
        "requirements": SpecPhase.REQUISITOS,
        "model": SpecPhase.MODELO,
    }
    return reverse.get(api_phase, SpecPhase.CARACTERISTICAS)


def _changes_to_plan(changes: list[ChangeInputView]) -> list[PlanCambio]:
    result: list[PlanCambio] = []
    for _idx, c in enumerate(changes):
        change_id = PlanChangeId(f"chg_eval_{ULID().hex}")
        result.append(
            PlanCambio(
                id=change_id,
                section=c.section,
                description=c.section,
                diff=DiffCambio(before=c.diff_before, after=c.diff_after),
            )
        )
    return result


@router.post(
    "/evaluate",
    summary="Evaluar consistencia entre fases",
    description="Evalúa el impacto de cambios sobre artefactos de fases adyacentes.",
    response_model=ConsistencyReportView,
    operation_id="evaluate_consistency",
)
async def evaluate_consistency(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Annotated[EvaluateConsistencyRequestView, Body(...)],
    evaluator: Annotated[ConsistencyEvaluator, Depends(_consistency_evaluator)],
    feature_repo: Annotated[FeatureRepository, Depends(_feature_repo)],
    requirement_repo: Annotated[RequirementRepository, Depends(_requirement_repo)],
    diagram_repo: Annotated[ActivityDiagramRepository, Depends(_diagram_repo)],
) -> ConsistencyReportView:
    report_id = f"cnr_{ULID().hex}"

    try:
        source_phase = _resolve_origin_phase(request.phase_origin)
    except HTTPException:
        raise

    applied_changes = _changes_to_plan(request.changes)
    targets = _resolve_targets(request.phase_destination)

    downstream_impact: list[ImpactItemView] = []
    upstream_impact: list[ImpactItemView] = []

    for target_api in targets:
        target_spec = _to_spec_phase(target_api)
        api_phase = _to_api_phase(target_spec)

        try:
            result = await evaluator.evaluate(
                source_phase=source_phase,
                target_phase=target_spec,
                project_id=ProjectId(project_id),
                applied_changes=applied_changes,
            )
        except Exception:
            _log.warning(
                "consistency.router.evaluate_failed",
                project_id=project_id,
                source=source_phase,
                target=target_spec,
                exc_info=True,
            )
            continue

        items = await _enrich_affected(
            result.affected_artifact_ids,
            api_phase,
            target_spec,
            feature_repo,
            requirement_repo,
            diagram_repo,
        )

        if _is_upstream(api_phase, request.phase_origin):
            upstream_impact.extend(items)
        else:
            downstream_impact.extend(items)

    return ConsistencyReportView(
        id=report_id,
        phase_origin=request.phase_origin,
        own_changes=request.changes,
        upstream_impact=upstream_impact if upstream_impact else None,
        downstream_impact=downstream_impact if downstream_impact else None,
        created_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


async def _enrich_affected(
    artifact_ids: list[str],
    api_phase: str,
    target_spec: SpecPhase,
    feature_repo: FeatureRepository,
    requirement_repo: RequirementRepository,
    diagram_repo: ActivityDiagramRepository,
) -> list[ImpactItemView]:
    items: list[ImpactItemView] = []

    if target_spec in {SpecPhase.CARACTERISTICAS, SpecPhase.REQUISITOS, SpecPhase.MODELO}:
        for fid_str in artifact_ids:
            from kosmo.contracts.sdd.ids import FeatureId

            feature = await feature_repo.by_id(FeatureId(fid_str))
            if feature is None:
                continue

            if target_spec == SpecPhase.CARACTERISTICAS:
                items.append(
                    ImpactItemView(
                        phase=api_phase,
                        artifact_id=fid_str,
                        artifact_type="Feature",
                        artifact_label=feature.display_id,
                        section="title",
                        rationale="El cambio en Descubrimiento afecta esta característica.",
                    )
                )
            elif target_spec == SpecPhase.REQUISITOS:
                req_md = await requirement_repo.by_feature_id(feature.id)
                if req_md is not None:
                    items.append(
                        ImpactItemView(
                            phase=api_phase,
                            artifact_id=fid_str,
                            artifact_type="EARSRequirement",
                            artifact_label=f"REQ-{feature.display_id}",
                            section="estructura EARS",
                            rationale="El cambio en Descubrimiento afecta los requisitos de esta característica.",
                        )
                    )
            elif target_spec == SpecPhase.MODELO:
                diagram_exists = await diagram_repo.exists(feature.id)
                if diagram_exists:
                    items.append(
                        ImpactItemView(
                            phase=api_phase,
                            artifact_id=fid_str,
                            artifact_type="ActivityDiagram",
                            artifact_label=f"Diagrama {feature.display_id}",
                            section="diagram",
                            rationale="El cambio en Descubrimiento afecta el diagrama de esta característica.",
                        )
                    )

    return items


def _is_upstream(api_phase: str, phase_origin: str) -> bool:
    order = ["discovery", "features", "requirements", "model"]
    try:
        return order.index(api_phase) < order.index(phase_origin)
    except ValueError:
        return False
