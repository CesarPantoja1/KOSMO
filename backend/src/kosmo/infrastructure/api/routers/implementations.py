import json
from collections.abc import AsyncGenerator
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sse_starlette.sse import EventSourceResponse

from kosmo.application.codegen.generate_feature_implementation import (
    GenerateFeatureImplementationInput,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.ids import FeatureId, ImplementationId
from kosmo.domain.codegen.path_safety import UnsafePathError, ensure_safe_path
from kosmo.infrastructure.api.composition import AppContainer
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.dependencies.container import get_container
from kosmo.infrastructure.api.implementation_broker import broker
from kosmo.infrastructure.api.schemas import (
    GenerateImplementationRequest,
    GenerateImplementationResponse,
    ImplementationFileContentResponse,
    ImplementationRecordResponse,
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
    container: Annotated[AppContainer, Depends(get_container)],
) -> GenerateImplementationResponse:
    use_case = container.codegen.generate_feature_implementation

    feature_id_obj = FeatureId(request.feature_id)
    impl_id = f"impl_{feature_id_obj}"

    input_data = GenerateFeatureImplementationInput(
        feature_id=feature_id_obj,
        max_retries=request.max_retries,
    )

    broker.start_implementation(
        implementation_id=impl_id,
        use_case=use_case,
        input_data=input_data,
    )

    return GenerateImplementationResponse(implementation_id=impl_id)


@router.get(
    "",
    response_model=ImplementationRecordResponse,
    summary="Obtener implementación por característica",
    description="Devuelve el registro persistido de la implementación de una característica, "
    "o 404 si aún no existe. Es la fuente de verdad para que el frontend no pida "
    "regenerar lo ya implementado.",
)
async def get_implementation_by_feature(
    feature_id: Annotated[str, Query(min_length=1, description="ID de la característica")],
    _principal: Annotated[Principal, Depends(get_principal)],
    container: Annotated[AppContainer, Depends(get_container)],
) -> ImplementationRecordResponse:
    impl = await container.repos.implementations.by_feature_id(FeatureId(feature_id))
    if impl is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró una implementación para la característica {feature_id}",
        )
    return ImplementationRecordResponse(
        implementation_id=str(impl.id),
        feature_id=str(impl.feature_id),
        project_id=str(impl.project_id),
        status=str(getattr(impl.status, "value", impl.status)),
        generated_files=list(impl.generated_files),
        updated_at=impl.updated_at,
    )


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
    async def event_publisher() -> AsyncGenerator[dict[str, Any]]:
        async for event in broker.subscribe(implementation_id):
            event_type = getattr(event.event_type, "value", str(event.event_type))
            yield {
                "event": event_type,
                "data": json.dumps(
                    {
                        "event_type": event_type,
                        "session_id": event.session_id,
                        "data": event.data,
                        "timestamp": event.timestamp.isoformat(),
                    }
                ),
            }

    return EventSourceResponse(event_publisher())


@router.get(
    "/{implementation_id}/files/content",
    response_model=ImplementationFileContentResponse,
    summary="Leer contenido de un archivo generado",
    description="Devuelve el contenido de un archivo del workspace de la implementación, "
    "validando que la ruta permanezca dentro del workspace.",
)
async def get_implementation_file_content(
    implementation_id: str,
    path: Annotated[str, Query(min_length=1, description="Ruta relativa del archivo dentro del workspace")],
    _principal: Annotated[Principal, Depends(get_principal)],
    container: Annotated[AppContainer, Depends(get_container)],
) -> ImplementationFileContentResponse:
    impl = await container.repos.implementations.by_id(ImplementationId(implementation_id))
    if impl is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la implementación {implementation_id}",
        )

    workspace = await container.repos.workspaces.by_project_id(impl.project_id)
    if workspace is None or not workspace.workspace_dir:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El workspace de la implementación no está disponible",
        )

    try:
        file_path = ensure_safe_path(path, workspace.workspace_dir)
    except UnsafePathError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"La ruta '{path}' no es válida: debe permanecer dentro del workspace",
        ) from None

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el archivo '{path}' en el workspace",
        )

    return ImplementationFileContentResponse(path=path, content=file_path.read_text(encoding="utf-8"))
