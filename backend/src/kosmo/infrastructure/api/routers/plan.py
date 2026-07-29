from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from kosmo.application.chat.manage_plan_changes import ManagePlanChangesUseCase
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import PlanChangeNotFoundError, ProjectNotFoundError
from kosmo.contracts.sdd.ids import PlanChangeId, ProjectId
from kosmo.infrastructure.api.schemas import (
    AddPlanChangeRequest,
    ApplyBatchRequest,
    BatchResultView,
    HttpErrorResponse,
    PlanStateView,
)

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/plan",
    tags=["plan"],
    responses={
        401: {"model": HttpErrorResponse, "description": "Token ausente, inválido o expirado"},
        404: {"model": HttpErrorResponse, "description": "Proyecto o recurso no encontrado"},
    },
)


def _manage_plan_changes(request: Request) -> ManagePlanChangesUseCase:
    return request.app.state.manage_plan_changes


@router.get(
    "",
    summary="Obtener estado del plan de cambios",
    description="Devuelve todos los cambios acumulados en el plan para una fase y contexto específicos.",
    response_model=PlanStateView,
    operation_id="get_plan_state",
)
async def get_plan_state(
    project_id: str,
    phase: Annotated[SpecPhase, Query(..., description="Fase cuyos cambios se consultan")],
    uc: Annotated[ManagePlanChangesUseCase, Depends(_manage_plan_changes)],
    context: Annotated[str | None, Query(description="Contexto específico (opcional para Descubrimiento)")] = None,
) -> PlanStateView:
    try:
        plan_state_output = await uc.get_plan_state(
            project_id=ProjectId(project_id),
            phase=phase,
            context_id=context,
        )
        return PlanStateView.from_domain(plan_state_output)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.delete(
    "",
    summary="Descartar plan de cambios completo",
    description=(
        "Descarta todos los cambios pendientes del plan para una fase y contexto. "
        "Requiere confirmación del usuario en el frontend."
    ),
    status_code=status.HTTP_200_OK,
    operation_id="discard_plan",
)
async def discard_plan(
    project_id: str,
    phase: Annotated[SpecPhase, Query(..., description="Fase cuyo plan se descarta")],
    uc: Annotated[ManagePlanChangesUseCase, Depends(_manage_plan_changes)],
    context: Annotated[str | None, Query(description="Contexto específico (opcional para Descubrimiento)")] = None,
) -> None:
    try:
        await uc.discard_plan(
            project_id=ProjectId(project_id),
            phase=phase,
            context_id=context,
        )
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/changes",
    summary="Agregar cambio al plan",
    description="Agrega una sugerencia de cambio (proveniente del chat u otro origen) al plan de cambios.",
    response_model=PlanStateView,
    operation_id="add_plan_change",
)
async def add_plan_change(
    project_id: str,
    request: AddPlanChangeRequest,
    phase: Annotated[SpecPhase, Query(..., description="Fase a la que pertenece el cambio")],
    uc: Annotated[ManagePlanChangesUseCase, Depends(_manage_plan_changes)],
    context: Annotated[str | None, Query(description="Contexto específico (opcional)")] = None,
) -> PlanStateView:
    try:
        plan_state_output = await uc.add_change(
            project_id=ProjectId(project_id),
            phase=phase,
            change_id=request.change_id,
            section=request.section,
            description=request.description,
            diff_before=request.diff_before,
            diff_after=request.diff_after,
            context_id=context,
            rationale=request.rationale,
        )
        return PlanStateView.from_domain(plan_state_output)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.delete(
    "/changes/{change_id}",
    summary="Quitar cambio del plan",
    description="Remueve un cambio individual del plan sin aplicarlo.",
    response_model=PlanStateView,
    operation_id="remove_plan_change",
)
async def remove_plan_change(
    project_id: str,
    change_id: str,
    phase: Annotated[SpecPhase, Query(..., description="Fase a la que pertenece el cambio")],
    uc: Annotated[ManagePlanChangesUseCase, Depends(_manage_plan_changes)],
    context: Annotated[str | None, Query(description="Contexto específico (opcional)")] = None,
) -> PlanStateView:
    try:
        plan_state_output = await uc.remove_change(
            project_id=ProjectId(project_id),
            phase=phase,
            change_id=PlanChangeId(change_id),
            context_id=context,
        )
        return PlanStateView.from_domain(plan_state_output)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PlanChangeNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/apply",
    summary="Aplicar lote de cambios",
    description="Aplica atómicamente un batch de cambios aceptados sobre los documentos. (Not Implemented Yet)",
    response_model=BatchResultView,
    operation_id="apply_batch",
)
async def apply_batch(
    _project_id: str,
    _request: ApplyBatchRequest,
) -> BatchResultView:
    # Endpoint stub para la tarea T17, se implementará completamente en HU-15.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="ApplyBatchUseCase no está implementado aún en esta tarea.",
    )
