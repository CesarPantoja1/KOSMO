from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from kosmo.application.traceability.manage_traceability_navigation import (
    ManageTraceabilityNavigationUseCase,
    TraceabilityNavigationInput,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.infrastructure.api.dependencies.auth import get_principal, require_project_owner
from kosmo.infrastructure.api.dependencies.container import get_container
from kosmo.infrastructure.api.schemas import TraceabilityNavigationOutputView

router = APIRouter(prefix="/api/v1/traceability", tags=["Traceability"])


def _manage_traceability_navigation(request: Request) -> ManageTraceabilityNavigationUseCase:
    return ManageTraceabilityNavigationUseCase(feature_repo=get_container(request).repos.features)


@router.get("/{entity_id}/navigation", response_model=TraceabilityNavigationOutputView)
async def check_traceability_navigation(
    entity_id: str,
    level: SpecPhase,
    use_case: Annotated[ManageTraceabilityNavigationUseCase, Depends(_manage_traceability_navigation)],
    principal: Annotated[Principal, Depends(get_principal)],
    request: Request,
) -> TraceabilityNavigationOutputView:
    """Verifica si la edición está permitida en este nivel o sugiere redirección."""
    container = get_container(request)
    if hasattr(container, "repos"):
        project_id = None
        if hasattr(container.repos, "features"):
            feature = await container.repos.features.by_id(FeatureId(entity_id))
            if feature is not None:
                project_id = feature.project_id
            elif level in (SpecPhase.REQUISITOS, SpecPhase.MODELO):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Característica {entity_id} no encontrada",
                )
        if project_id is None:
            project_id = entity_id
        await require_project_owner(container, project_id, principal)

    input_data = TraceabilityNavigationInput(entity_id=entity_id, level=level)
    output = await use_case.execute(input_data)

    return TraceabilityNavigationOutputView(
        permitted=output.permitted,
        redirect_message=output.redirect_message,
        source_entity_name=output.source_entity_name,
        source_entity_id=output.source_entity_id,
        source_level=output.source_level,
    )
