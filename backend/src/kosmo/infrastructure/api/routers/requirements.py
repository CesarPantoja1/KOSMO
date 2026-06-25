from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from kosmo.application.requirements import (
    GenerateEARSInput,
    GenerateEARSUseCase,
    GetRequirementsUseCase,
    SaveRequirementsUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    FeatureNotFoundError,
    LLMInvocationError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
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


async def _resolve_feature_id(request: Request, project_id: str, id_or_slug: str) -> FeatureId:
    if id_or_slug.startswith("feat_"):
        return FeatureId(id_or_slug)

    feature_repo = request.app.state.feature_repo
    features = await feature_repo.list_by_project(ProjectId(project_id))
    match = next((f for f in features if f.slug == id_or_slug), None)
    if match is None:
        raise FeatureNotFoundError(
            feature_id=id_or_slug,
            instance=f"/api/v1/features/{id_or_slug}/requirements",
        )
    return match.id


@router.post(
    "/generate",
    summary="Generar requisitos EARS",
    description=(
        "Genera requisitos utilizando el estándar EARS para la característica especificada."
    ),
    status_code=status.HTTP_200_OK,
)
async def generate_requirements(
    feature_id: str,
    body: GenerateRequirementsRequest,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Request,
) -> dict[str, Any]:
    fid = await _resolve_feature_id(request, body.project_id, feature_id)
    uc = cast("GenerateEARSUseCase", request.app.state.generate_ears)

    try:
        output = await uc.execute(
            GenerateEARSInput(
                project_id=ProjectId(body.project_id),
                feature_id=fid,
            )
        )
    except (ProjectNotFoundError, FeatureNotFoundError, DocumentNotFoundError) as exc:
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
        "requirements_markdown": output.phase_output.requirements_markdown,
        "total": len(output.requirements),
    }


@router.get(
    "",
    summary="Obtener requisitos de una característica",
    description=(
        "Recupera los requisitos en formato Markdown asociados a la característica especificada."
    ),
)
async def get_requirements(
    feature_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Request,
    project_id: str = Query(...),
) -> dict[str, str]:
    fid = await _resolve_feature_id(request, project_id, feature_id)
    uc = cast("GetRequirementsUseCase", request.app.state.get_requirements)

    try:
        markdown = await uc.execute(
            project_id=ProjectId(project_id),
            feature_id=fid,
        )
    except (ProjectNotFoundError, FeatureNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc

    return {"document_markdown": markdown or ""}


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
    fid = await _resolve_feature_id(request, body.project_id, feature_id)
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
