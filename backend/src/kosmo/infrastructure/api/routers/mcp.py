"""Router MCP — Expone tools de contexto para que OpenCode consulte bajo demanda."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import ActivityDiagramRepository, RequirementRepository

router = APIRouter(prefix="/mcp", tags=["MCP Tools"])


class MCPToolRequest(BaseModel):
    """Solicitud de una tool MCP con el identificador de la característica."""

    feature_id: str = Field(min_length=1, description="Identificador de la característica")


class MCPToolResponse(BaseModel):
    """Respuesta de una tool MCP con el contenido solicitado."""

    feature_id: str
    content: str


def _get_requirement_repo(request: Request) -> RequirementRepository:
    return request.app.state.requirement_repo  # type: ignore[no-any-return]


def _get_diagram_repo(request: Request) -> ActivityDiagramRepository:
    return request.app.state.diagram_repo  # type: ignore[no-any-return]


@router.post(
    "/tools/get_requirements",
    response_model=MCPToolResponse,
    summary="Obtener requisitos EARS de una característica",
    responses={404: {"description": "Requisitos no encontrados para la característica indicada"}},
)
async def get_requirements(body: MCPToolRequest, request: Request) -> MCPToolResponse:
    """Retorna los requisitos EARS en formato markdown para la característica indicada."""
    repo = _get_requirement_repo(request)
    markdown = await repo.by_feature_id(FeatureId(body.feature_id))
    if markdown is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontraron requisitos EARS para la característica {body.feature_id}",
        )
    return MCPToolResponse(feature_id=body.feature_id, content=markdown)


@router.post(
    "/tools/get_activity_diagram",
    response_model=MCPToolResponse,
    summary="Obtener diagrama de actividad de una característica",
    responses={404: {"description": "Diagrama de actividad no encontrado para la característica indicada"}},
)
async def get_activity_diagram(body: MCPToolRequest, request: Request) -> MCPToolResponse:
    """Retorna el diagrama de actividad en formato PlantUML para la característica indicada."""
    repo = _get_diagram_repo(request)
    diagram = await repo.by_feature_id(FeatureId(body.feature_id))
    if diagram is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró diagrama de actividad para la característica {body.feature_id}",
        )
    return MCPToolResponse(feature_id=body.feature_id, content=diagram.diagram_syntax)
