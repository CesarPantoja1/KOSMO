from typing import Annotated

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status

from kosmo.application.chat.apply_plan_changes import (
    ApplyPlanChangesInput,
    ApplyPlanChangesUseCase,
    revert_to_version,
)
from kosmo.application.chat.manage_plan_changes import ManagePlanChangesUseCase
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    PlanChangeNotFoundError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.ids import PlanChangeId, ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.schemas import (
    AddPlanChangeRequest,
    AppliedChangeItemView,
    ApplyBatchRequest,
    BatchResultView,
    FailedChangeItemView,
    HttpErrorResponse,
    PhaseNotificationList,
    PhaseNotificationView,
    PlanStateView,
)

_log = structlog.get_logger(__name__)

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


def _apply_plan_changes(request: Request) -> ApplyPlanChangesUseCase:
    return request.app.state.apply_plan_changes


@router.get(
    "",
    summary="Obtener estado del plan de cambios",
    description="Devuelve los cambios activos del plan (pending, added, conflict) para una fase y contexto.",
    response_model=PlanStateView,
    operation_id="get_plan_state",
)
async def get_plan_state(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.problem.detail) from e


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
    _principal: Annotated[Principal, Depends(get_principal)],
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.problem.detail) from e


@router.post(
    "/changes",
    summary="Agregar cambio al plan",
    description="Agrega una sugerencia de cambio (proveniente del chat u otro origen) al plan de cambios.",
    response_model=PlanStateView,
    operation_id="add_plan_change",
)
async def add_plan_change(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.problem.detail) from e


@router.delete(
    "/changes/{change_id}",
    summary="Quitar cambio del plan",
    description="Remueve un cambio individual del plan sin aplicarlo.",
    response_model=PlanStateView,
    operation_id="remove_plan_change",
)
async def remove_plan_change(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.problem.detail) from e
    except PlanChangeNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.problem.detail) from e


@router.post(
    "/apply",
    summary="Aplicar lote de cambios",
    description="Aplica un batch de cambios al documento de Descubrimiento",
    response_model=BatchResultView,
    operation_id="apply_batch",
)
async def apply_batch(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Annotated[ApplyBatchRequest, Body(...)],
    uc: Annotated[ApplyPlanChangesUseCase, Depends(_apply_plan_changes)],
) -> BatchResultView:
    try:
        output = await uc.execute(
            ApplyPlanChangesInput(
                project_id=ProjectId(project_id),
                phase=request.phase,
                change_ids=[PlanChangeId(cid) for cid in request.changes],
            )
        )
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.problem.detail) from e
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.problem.detail) from e
    except ValueError as e:
        _log.error("plan.apply_value_error", detail=str(e), exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    applied = [AppliedChangeItemView(change_id=str(c.id), section=c.section) for c in output.applied_changes]
    failed = [
        FailedChangeItemView(change_id=str(fc.id), section=fc.section, error=fc.reason) for fc in output.failed_changes
    ]

    propagation: PhaseNotificationList | None = None
    if output.propagation is not None:
        affected = [
            PhaseNotificationView(
                phase=p.phase,
                affected_count=p.affected_count,
                affected_ids=p.affected_ids,
            )
            for p in output.propagation.affected_phases
            if p.affected_count > 0
        ]
        if affected:
            propagation = PhaseNotificationList(affected_phases=affected)

    return BatchResultView(
        applied_count=output.applied_count,
        failed_count=output.failed_count,
        applied=applied,
        failed=failed,
        propagation=propagation,
    )


def _document_repo(request: Request) -> DocumentRepository:
    return request.app.state.document_repo


@router.post(
    "/revert",
    summary="Revertir a una versión anterior del documento",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Versión no encontrada."},
    },
)
async def revert_document(
    project_id: str,
    version_id: Annotated[str, Body(..., embed=True)],
    _principal: Annotated[Principal, Depends(get_principal)],
    doc_repo: Annotated[DocumentRepository, Depends(_document_repo)],
):
    result = await revert_to_version(
        document_repo=doc_repo,
        project_id=ProjectId(project_id),
        version_id=version_id,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Versión no encontrada",
        )
    return {"status": "ok", "version_id": version_id}
