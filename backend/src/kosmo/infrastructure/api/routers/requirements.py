from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from kosmo.application.requirements import (
    GenerateEARSInput,
    GenerateEARSUseCase,
    GetRequirementsUseCase,
    RefineRequirementsInput,
    RefineRequirementsUseCase,
    RegenerateRequirementsInput,
    RegenerateRequirementsUseCase,
    SaveRequirementsUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import (
    FeatureNotFoundError,
    LLMInvocationError,
    ProjectNotFoundError,
    RequirementsNotFoundError,
)
from kosmo.contracts.sdd.ids import FeatureId, PlanChangeId, ProjectId
from kosmo.domain.pipeline.feature_resolver import resolve_feature_id
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.schemas import (
    PhaseNotificationList,
    PhaseNotificationView,
)

router = APIRouter(
    prefix="/api/v1/features/{feature_id}/requirements",
    tags=["requirements"],
)


class GenerateRequirementsRequest(BaseModel):
    project_id: str


class SaveRequirementsRequest(BaseModel):
    project_id: str
    markdown: str


class RefineRequirementsRequest(BaseModel):
    project_id: str
    instructions: str = Field(min_length=1, max_length=500)


async def _get_feature_id(request: Request, project_id: str, id_or_slug: str) -> FeatureId:
    fid = await resolve_feature_id(request.app.state.feature_repo, ProjectId(project_id), id_or_slug)
    if fid is None:
        raise FeatureNotFoundError(feature_id=id_or_slug, instance=f"/api/v1/features/{id_or_slug}/requirements")
    return fid


@router.post(
    "/generate",
    summary="Generar requisitos EARS",
    description="Genera requisitos EARS para la característica indicada.",
    status_code=status.HTTP_200_OK,
)
async def generate_requirements(
    feature_id: str,
    body: GenerateRequirementsRequest,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Request,
) -> dict[str, Any]:
    fid = await _get_feature_id(request, body.project_id, feature_id)
    uc = cast("GenerateEARSUseCase", request.app.state.generate_ears)

    output = await uc.execute(GenerateEARSInput(project_id=ProjectId(body.project_id), feature_id=fid))
    return {
        "project_id": str(output.project_id),
        "feature_id": str(output.feature_id),
        "feature_number": output.phase_output.feature_number,
        "document_markdown": output.phase_output.requirements_markdown,
        "total": len(output.requirements),
        "requirements": [
            {
                "id": str(r.id),
                "title": r.title,
                "statement": r.statement,
                "pattern": r.pattern.value if hasattr(r.pattern, "value") else r.pattern,
                "acceptance_criteria": r.acceptance_criteria,
            }
            for r in output.requirements
        ],
    }


@router.get(
    "",
    summary="Obtener requisitos de una característica",
    description=("Recupera los requisitos en formato Markdown asociados a la característica especificada."),
)
async def get_requirements(
    feature_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Request,
    project_id: str = Query(...),
) -> dict[str, Any]:
    fid = await _get_feature_id(request, project_id, feature_id)
    uc = cast("GetRequirementsUseCase", request.app.state.get_requirements)

    try:
        output = await uc.execute(
            project_id=ProjectId(project_id),
            feature_id=fid,
        )
    except (ProjectNotFoundError, FeatureNotFoundError, RequirementsNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc

    return {"document_markdown": output.markdown or "", "total": output.total}


@router.put(
    "",
    summary="Guardar/actualizar requisitos",
    description="Actualiza el documento Markdown de requisitos de la característica especificada.",
)
async def save_requirements(
    feature_id: str,
    body: SaveRequirementsRequest,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Request,
) -> dict[str, str]:
    fid = await _get_feature_id(request, body.project_id, feature_id)
    uc = cast("SaveRequirementsUseCase", request.app.state.save_requirements)

    try:
        await uc.execute(
            project_id=ProjectId(body.project_id),
            feature_id=fid,
            markdown=body.markdown,
        )
    except (ProjectNotFoundError, FeatureNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc

    return {"feature_id": feature_id, "message": "ok"}


@router.post(
    "/refine",
    summary="Refinar requisitos EARS con IA",
    description=(
        "Refina los requisitos de una característica aplicando las instrucciones "
        "proporcionadas por el usuario mediante inteligencia artificial. "
        "Requiere que la característica ya tenga requisitos generados; de lo contrario "
        "devuelve 404. Los requisitos actuales se conservan intactos si la IA falla. "
        "Las instrucciones no pueden exceder los 500 caracteres."
    ),
    status_code=status.HTTP_200_OK,
)
async def refine_requirements(
    feature_id: str,
    body: RefineRequirementsRequest,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Request,
) -> dict[str, Any]:
    fid = await _get_feature_id(request, body.project_id, feature_id)
    uc = cast("RefineRequirementsUseCase", request.app.state.refine_requirements)

    try:
        output = await uc.execute(
            RefineRequirementsInput(
                project_id=ProjectId(body.project_id),
                feature_id=fid,
                user_instructions=body.instructions,
            )
        )
    except (ProjectNotFoundError, FeatureNotFoundError, RequirementsNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc
    except LLMInvocationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.problem.detail,
        ) from exc

    return {
        "feature_id": str(output.feature_id),
        "feature_number": output.phase_output.feature_number,
        "document_markdown": output.phase_output.requirements_markdown,
        "total": len(output.requirements),
    }


class PropagateRequirementsRequest(BaseModel):
    project_id: str
    applied_change_ids: list[str] = []


@router.post(
    "/propagate",
    summary="Propagar cambios desde Requisitos",
    description=(
        "Evalúa el impacto de los cambios aplicados en los requisitos de una "
        "característica en ambas direcciones: upstream hacia Características y "
        "Descubrimiento, downstream hacia Modelo. Retorna las fases afectadas "
        "para que el wizard actualice sus insignias de advertencia."
    ),
    response_model=PhaseNotificationList,
    status_code=status.HTTP_200_OK,
)
async def propagate_requirement_changes(
    feature_id: str,
    body: PropagateRequirementsRequest,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Request,
) -> PhaseNotificationList:
    from kosmo.application.consistency.propagate_changes import (
        PropagateChangesInput,
    )

    uc = request.app.state.propagate_requirement_changes

    try:
        output = await uc.execute(
            PropagateChangesInput(
                project_id=ProjectId(body.project_id),
                source_phase=SpecPhase.REQUISITOS,
                applied_change_ids=[PlanChangeId(cid) for cid in body.applied_change_ids],
                feature_id=FeatureId(feature_id),
            )
        )
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.problem.detail) from e

    return PhaseNotificationList(
        affected_phases=[
            PhaseNotificationView(
                phase=p.phase,
                affected_count=p.affected_count,
                affected_ids=p.affected_ids,
            )
            for p in output.affected_phases
        ]
    )


class RegenerateRequirementsResponse(BaseModel):
    artifact_id: str
    content: str
    phase: str


@router.post(
    "/regenerate",
    summary="Regenerar requisitos EARS con IA",
    description=(
        "Regenera los requisitos de una característica a partir del estado "
        "actual de la característica padre, manteniendo la estructura EARS y "
        "los criterios de aceptación en formato Dado-Cuando-Entonces."
    ),
    response_model=RegenerateRequirementsResponse,
    status_code=status.HTTP_200_OK,
)
async def regenerate_requirements(
    feature_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Request,
    project_id: str = Query(...),
) -> RegenerateRequirementsResponse:
    uc = cast("RegenerateRequirementsUseCase", request.app.state.regenerate_requirements)

    try:
        output = await uc.execute(
            RegenerateRequirementsInput(
                project_id=ProjectId(project_id),
                feature_id=FeatureId(feature_id),
            )
        )
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.problem.detail) from e
    except FeatureNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.problem.detail) from e
    except LLMInvocationError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=e.problem.detail) from e

    return RegenerateRequirementsResponse(
        artifact_id=output.artifact_id,
        content=output.content,
        phase=output.phase,
    )
