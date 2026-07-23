from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from kosmo.application.modelo import (
    GenerateActivityDiagramUseCase,
    GenerateDiagramInput,
    GetActivityDiagramUseCase,
    GetDiagramInput,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.errors import (
    DiagramNotFoundError,
    FeatureNotFoundError,
    LLMInvocationError,
    ProjectNotFoundError,
    RequirementsNotFoundError,
)
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.infrastructure.api.dependencies.auth import get_principal

router = APIRouter(
    prefix="/api/v1/features/{feature_id}/diagram",
    tags=["modelo"],
)


class GenerateDiagramRequest(BaseModel):
    project_id: str


async def _resolve_feature_id(request: Request, project_id: str, id_or_slug: str) -> FeatureId:
    if id_or_slug.startswith("feat_"):
        return FeatureId(id_or_slug)

    feature_repo = request.app.state.feature_repo
    features = await feature_repo.list_by_project(ProjectId(project_id))
    match = next((f for f in features if f.slug == id_or_slug), None)
    if match is None:
        raise FeatureNotFoundError(
            feature_id=id_or_slug,
            instance=f"/api/v1/features/{id_or_slug}/diagram",
        )
    return match.id


@router.post(
    "/generate",
    summary="Generar diagrama de actividad",
    description="Genera un diagrama de actividad PlantUML para la característica especificada.",
    status_code=status.HTTP_200_OK,
)
async def generate_diagram(
    feature_id: str,
    body: GenerateDiagramRequest,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Request,
) -> dict[str, Any]:
    fid = await _resolve_feature_id(request, body.project_id, feature_id)
    uc = cast("GenerateActivityDiagramUseCase", request.app.state.generate_diagram)

    try:
        output = await uc.execute(
            GenerateDiagramInput(
                project_id=ProjectId(body.project_id),
                feature_id=fid,
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
        "id": str(output.diagram.id),
        "feature_id": str(output.diagram.feature_id),
        "diagram_syntax": output.diagram.diagram_syntax,
        "created_at": output.diagram.created_at.isoformat(),
        "updated_at": output.diagram.updated_at.isoformat(),
    }


@router.get(
    "",
    summary="Obtener diagrama de actividad",
    description="Recupera el diagrama de actividad PlantUML existente de la característica.",
)
async def get_diagram(
    feature_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Request,
    project_id: str = Query(...),
) -> dict[str, Any]:
    fid = await _resolve_feature_id(request, project_id, feature_id)
    uc = cast("GetActivityDiagramUseCase", request.app.state.get_diagram)

    try:
        output = await uc.execute(
            GetDiagramInput(
                project_id=ProjectId(project_id),
                feature_id=fid,
            )
        )
    except (ProjectNotFoundError, FeatureNotFoundError, DiagramNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc

    return {
        "id": str(output.diagram.id),
        "feature_id": str(output.diagram.feature_id),
        "diagram_syntax": output.diagram.diagram_syntax,
        "created_at": output.diagram.created_at.isoformat(),
        "updated_at": output.diagram.updated_at.isoformat(),
    }
