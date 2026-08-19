from collections.abc import AsyncGenerator
import json
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, status
from sse_starlette.sse import EventSourceResponse

from kosmo.application.codegen.generate_feature_implementation import (
    GenerateFeatureImplementationInput,
    GenerateFeatureImplementationUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.dependencies.container import get_container
from kosmo.infrastructure.api.implementation_broker import broker
from kosmo.infrastructure.api.schemas import (
    GenerateImplementationRequest,
    GenerateImplementationResponse,
)

_log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/implementations", tags=["Implementations"])


@router.post(
    "",
    response_model=GenerateImplementationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Iniciar implementación",
    description="Inicia asíncronamente la generación de código para una característica.",
)
async def start_implementation(
    request: GenerateImplementationRequest,
    _principal: Annotated[Principal, Depends(get_principal)],
    container: Annotated[Any, Depends(get_container)],
) -> GenerateImplementationResponse:
    # 1. Obtener UseCase desde el container
    # Hacemos type ignore o importamos el container real
    use_case: GenerateFeatureImplementationUseCase = container.pipeline.generate_feature_implementation  # type: ignore[attr-defined]

    # 2. Generar el input y el ID
    feature_id_obj = FeatureId(request.feature_id)
    impl_id = f"impl_{feature_id_obj}"

    input_data = GenerateFeatureImplementationInput(
        feature_id=feature_id_obj,
        max_retries=request.max_retries,
    )

    # 3. Delegar al broker en memoria (background)
    broker.start_implementation(
        implementation_id=impl_id,
        use_case=use_case,
        input_data=input_data,
    )

    return GenerateImplementationResponse(implementation_id=impl_id)


@router.get(
    "/{implementation_id}/events",
    summary="Suscribirse a eventos",
    description="Flujo SSE para eventos en tiempo real de la implementación.",
)
async def stream_implementation_events(
    implementation_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
) -> EventSourceResponse:
    # El broker devuelve un AsyncGenerator[OpenCodeEvent, None]
    # SseEventSourceResponse itera sobre él y lo expone como Server-Sent Events.
    async def event_publisher() -> AsyncGenerator[dict[str, Any], None]:
        async for event in broker.subscribe(implementation_id):
            yield {
                "event": getattr(event.event_type, "value", str(event.event_type)),
                "data": json.dumps(
                    {"session_id": event.session_id, "data": event.data, "timestamp": event.timestamp.isoformat()}
                ),
            }

    return EventSourceResponse(event_publisher())
