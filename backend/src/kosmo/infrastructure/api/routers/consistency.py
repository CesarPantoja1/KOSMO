from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from ulid import ULID

from kosmo.application.consistency.evaluate_project_consistency import (
    EvaluateProjectConsistencyInput,
    EvaluateProjectConsistencyOutput,
    EvaluateProjectConsistencyUseCase,
)
from kosmo.contracts import DiffCambio, PlanCambio
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import PlanChangeId, ProjectId
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.schemas import (
    ChangeInputView,
    ConsistencyReportView,
    EvaluateConsistencyRequestView,
    HttpErrorResponse,
    ImpactItemView,
)

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/consistency",
    tags=["consistency"],
    responses={
        401: {"model": HttpErrorResponse, "description": "Token ausente, inválido o expirado"},
        404: {"model": HttpErrorResponse, "description": "Proyecto no encontrado"},
    },
)


def _consistency_uc(request: Request) -> EvaluateProjectConsistencyUseCase:
    return request.app.state.evaluate_project_consistency


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
    uc: Annotated[EvaluateProjectConsistencyUseCase, Depends(_consistency_uc)],
) -> ConsistencyReportView:
    source_phase = _resolve_origin_phase(request.phase_origin)
    changes = _changes_to_plan(request.changes)
    targets = _resolve_targets(request.phase_destination)
    target_specs = [_to_spec_phase(t) for t in targets]

    result = await uc.execute(
        EvaluateProjectConsistencyInput(
            project_id=ProjectId(project_id),
            source_phase=source_phase,
            target_phases=target_specs,
            applied_changes=changes,
        )
    )

    return _to_view(result, request.phase_origin, request.changes)


def _resolve_origin_phase(phase_name: str) -> SpecPhase:
    reverse = {
        "discovery": SpecPhase.DESCUBRIMIENTO,
        "features": SpecPhase.CARACTERISTICAS,
        "requirements": SpecPhase.REQUISITOS,
    }
    if phase_name not in reverse:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fase de origen desconocida: '{phase_name}'.",
        )
    return reverse[phase_name]


def _resolve_targets(phase_destination: str | None) -> list[str]:
    if phase_destination:
        return [phase_destination]
    return ["caracteristicas", "requisitos", "modelo"]


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
    for c in changes:
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


def _to_view(
    output: EvaluateProjectConsistencyOutput,
    phase_origin: str,
    changes: list[ChangeInputView],
) -> ConsistencyReportView:
    from datetime import UTC, datetime

    upstream = [_impact_to_view(i) for i in output.upstream_impact] if output.upstream_impact else None
    downstream = [_impact_to_view(i) for i in output.downstream_impact] if output.downstream_impact else None
    return ConsistencyReportView(
        id=output.report_id,
        phase_origin=phase_origin,
        own_changes=changes,
        upstream_impact=upstream,
        downstream_impact=downstream,
        created_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def _impact_to_view(item: object) -> ImpactItemView:
    return ImpactItemView(
        phase=item.phase,  # type: ignore[reportAttributeAccessIssue]
        artifact_id=item.artifact_id,  # type: ignore[reportAttributeAccessIssue]
        artifact_type=item.artifact_type,  # type: ignore[reportAttributeAccessIssue]
        artifact_label=item.artifact_label,  # type: ignore[reportAttributeAccessIssue]
        section=item.section,  # type: ignore[reportAttributeAccessIssue]
        rationale=item.rationale,  # type: ignore[reportAttributeAccessIssue]
    )
