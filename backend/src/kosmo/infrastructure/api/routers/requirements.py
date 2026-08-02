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
    SaveRequirementsUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.errors import (
    FeatureNotFoundError,
    LLMInvocationError,
    ProjectNotFoundError,
    RequirementsNotFoundError,
)
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.domain.pipeline.feature_resolver import resolve_feature_id
from kosmo.infrastructure.api.dependencies.auth import get_principal

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
    except (ProjectNotFoundError, FeatureNotFoundError) as exc:
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
