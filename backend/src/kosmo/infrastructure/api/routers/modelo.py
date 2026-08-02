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
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.domain.pipeline.feature_resolver import resolve_feature_id
from kosmo.infrastructure.api.dependencies.auth import get_principal

router = APIRouter(
    prefix="/api/v1/features/{feature_id}/diagram",
    tags=["modelo"],
)


class GenerateDiagramRequest(BaseModel):
    project_id: str


async def _get_feature_id(request: Request, project_id: str, id_or_slug: str) -> FeatureId:
    fid = await resolve_feature_id(
        request.app.state.feature_repo, ProjectId(project_id), id_or_slug
    )
    if fid is None:
        raise FeatureNotFoundError(
            feature_id=id_or_slug,
            instance=f"/api/v1/features/{id_or_slug}/diagram",
        )
    return fid


@router.post(
    "/generate",
    summary="Generar diagrama de actividad (asíncrono)",
    description="Genera un diagrama PlantUML. Devuelve un job_id para seguir el progreso.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_diagram(
    feature_id: str,
    body: GenerateDiagramRequest,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Request,
) -> dict[str, str]:
    from kosmo.infrastructure.api.async_generation import launch_async

    fid = await _get_feature_id(request, body.project_id, feature_id)
    uc = cast("GenerateActivityDiagramUseCase", request.app.state.generate_diagram)

    job_id = await launch_async(
        request.app.state.async_job_store,
        "modelo_generate",
        body.project_id,
        uc.execute(GenerateDiagramInput(project_id=ProjectId(body.project_id), feature_id=fid)),
    )
    return {"job_id": job_id}


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
    fid = await _get_feature_id(request, project_id, feature_id)
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
        "created_at": output.diagram.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": output.diagram.updated_at.isoformat().replace("+00:00", "Z"),
    }
