from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from ulid import ULID

from kosmo.application.consistency.evaluate_project_consistency import (
    EvaluateProjectConsistencyInput,
    EvaluateProjectConsistencyUseCase,
)
from kosmo.contracts import DiffCambio, PlanCambio
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import PlanChangeId, ProjectId
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.schemas import (
    ChangeInputView,
    EvaluateConsistencyRequestView,
    HttpErrorResponse,
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
    description="Evalúa el impacto de cambios propuestos sobre artefactos del proyecto.",
    status_code=status.HTTP_200_OK,
)
async def evaluate_consistency(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Annotated[EvaluateConsistencyRequestView, Body(...)],
    uc: Annotated[EvaluateProjectConsistencyUseCase, Depends(_consistency_uc)],
) -> dict[str, Any]:
    source_phase = _resolve_origin_phase(request.phase_origin)
    changes = _changes_to_plan(request.changes)
    targets = _resolve_targets(request.phase_destination)
    target_specs = [_to_spec_phase(t) for t in targets]

    output = await uc.execute(
        EvaluateProjectConsistencyInput(
            project_id=ProjectId(project_id),
            source_phase=source_phase,
            target_phases=target_specs,
            applied_changes=changes,
        )
    )
    return {
        "report_id": output.report_id,
        "source_phase": output.source_phase,
        "upstream_impact": [_impact_dict(i) for i in output.upstream_impact],
        "downstream_impact": [_impact_dict(i) for i in output.downstream_impact],
    }


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


def _impact_dict(i: Any) -> dict[str, str]:
    return {
        "phase": i.phase,
        "artifact_id": i.artifact_id,
        "artifact_type": i.artifact_type,
        "artifact_label": i.artifact_label,
        "section": i.section,
        "rationale": i.rationale,
    }
