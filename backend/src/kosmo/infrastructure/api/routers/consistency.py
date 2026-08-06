from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from ulid import ULID

from kosmo.application.consistency.apply_consistency_impacts import ApplyConsistencyImpactsUseCase
from kosmo.application.consistency.cascade_consistency import CascadingConsistencyUseCase
from kosmo.application.consistency.evaluate_project_consistency import (
    EvaluateProjectConsistencyInput,
    EvaluateProjectConsistencyUseCase,
)
from kosmo.contracts import DiffCambio, PlanCambio
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.document import SPEC_TO_API_PHASE, SpecPhase
from kosmo.contracts.sdd.ids import PlanChangeId, ProjectId
from kosmo.infrastructure.api.async_generation import sse_consistency_response
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


def _cascade_uc(request: Request) -> CascadingConsistencyUseCase:
    return request.app.state.cascade_consistency


def _apply_uc(request: Request) -> ApplyConsistencyImpactsUseCase:
    return request.app.state.apply_consistency_impacts


@router.post(
    "/evaluate/stream",
    summary="Evaluar consistencia entre fases (SSE streaming)",
    description="Evalúa el impacto de cambios en cascada (features → requirements → model) con progreso SSE.",
    status_code=status.HTTP_200_OK,
)
async def evaluate_consistency_stream(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Annotated[EvaluateConsistencyRequestView, Body(...)],
    uc: Annotated[CascadingConsistencyUseCase, Depends(_cascade_uc)],
) -> StreamingResponse:
    source_phase = _resolve_origin_phase(request.phase_origin)
    changes = _changes_to_plan(request.changes)

    generator = uc.execute_stream(
        project_id=ProjectId(project_id),
        source_phase=source_phase,
        applied_changes=changes,
    )
    return await sse_consistency_response(generator)


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
    source_api_phase = SPEC_TO_API_PHASE.get(source_phase, source_phase.value)
    return {
        "report_id": output.report_id,
        "source_type": source_api_phase,
        "source_id": project_id,
        "your_changes": [
            {
                "change_id": str(c.id),
                "section": c.section,
                "description": c.description,
                "diff": {"before": c.diff.before, "after": c.diff.after},
                "accepted": True,
            }
            for c in changes
        ],
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
    return ["features", "requirements", "model"]


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
                description=c.description or c.section,
                diff=DiffCambio(before=c.diff_before, after=c.diff_after),
            )
        )
    return result


def _impact_dict(i: Any) -> dict[str, Any]:
    return {
        "id": i.id,
        "phase": i.phase,
        "targetId": i.target_id,
        "artifact_type": i.artifact_type,
        "targetDisplayId": i.target_display_id,
        "targetTitle": i.target_title,
        "section": i.section,
        "rationale": i.rationale,
        "diff": i.diff,
        "action": getattr(i, "action", "update"),
    }


class ApplyImpactsRequestView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    impacts: list[dict[str, object]] = Field(description="Impactos a aplicar")


@router.post(
    "/apply",
    summary="Aplicar impactos de consistencia",
    description="Aplica las acciones sugeridas sobre requisitos, caracteristicas y diagramas.",
    status_code=status.HTTP_200_OK,
)
async def apply_consistency_impacts(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Annotated[ApplyImpactsRequestView, Body(...)],
    uc: Annotated[ApplyConsistencyImpactsUseCase, Depends(_apply_uc)],
) -> dict[str, Any]:
    output = await uc.execute(project_id=ProjectId(project_id), impacts=request.impacts)
    return {
        "applied": [{"target_id": a.target_id, "artifact_type": a.artifact_type} for a in output.applied],
        "failed": [
            {"target_id": f.target_id, "artifact_type": f.artifact_type, "reason": f.reason} for f in output.failed
        ],
    }
