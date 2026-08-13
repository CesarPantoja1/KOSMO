from typing import Annotated

from fastapi import APIRouter, Depends, Request

from kosmo.application.traceability.manage_traceability_navigation import (
    ManageTraceabilityNavigationUseCase,
    TraceabilityNavigationInput,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.auth import Principal
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.dependencies.container import get_container
from kosmo.infrastructure.api.schemas import TraceabilityNavigationOutputView

router = APIRouter(prefix="/traceability", tags=["Traceability"])


def _manage_traceability_navigation(request: Request) -> ManageTraceabilityNavigationUseCase:
    return ManageTraceabilityNavigationUseCase(feature_repo=get_container(request).repos.features)


@router.get("/{entity_id}/navigation", response_model=TraceabilityNavigationOutputView)
async def check_traceability_navigation(
    entity_id: str,
    level: SpecPhase,
    use_case: Annotated[ManageTraceabilityNavigationUseCase, Depends(_manage_traceability_navigation)],
    _principal: Annotated[Principal, Depends(get_principal)],
) -> TraceabilityNavigationOutputView:
    """Verifica si la edición está permitida en este nivel o sugiere redirección."""
    input_data = TraceabilityNavigationInput(entity_id=entity_id, level=level)
    output = await use_case.execute(input_data)

    return TraceabilityNavigationOutputView(
        permitted=output.permitted,
        redirect_message=output.redirect_message,
        source_entity_name=output.source_entity_name,
        source_entity_id=output.source_entity_id,
        source_level=output.source_level,
    )
