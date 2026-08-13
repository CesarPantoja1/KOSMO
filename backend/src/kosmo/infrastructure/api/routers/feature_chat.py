from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from kosmo.application.chat.process_chat_regeneration import (
    ProcessChatRegenerationInput,
    ProcessChatRegenerationUseCase,
)
from kosmo.application.chat.validate_phase_context import (
    ValidatePhaseContextInput,
    ValidatePhaseContextUseCase,
)
from kosmo.application.features import (
    GetFeatureChatHistoryInput,
    GetFeatureChatHistoryUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    FeatureNotFoundError,
    LLMInvocationError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.dependencies.container import get_container
from kosmo.infrastructure.api.schemas import (
    ChatHistoryResponse,
    ChatResponse,
    SendChatRequest,
)

router = APIRouter(
    prefix="/api/v1/features/{feature_id}/chat",
    tags=["features"],
)


def _chat_regeneration_uc(request: Request) -> ProcessChatRegenerationUseCase:
    return get_container(request).pipeline.process_chat_regeneration


def _get_feature_chat_history(request: Request) -> GetFeatureChatHistoryUseCase:
    return get_container(request).features.get_feature_chat_history


def _validate_phase_context(request: Request) -> ValidatePhaseContextUseCase:
    return get_container(request).pipeline.validate_phase_context


@router.post(
    "",
    summary="Enviar mensaje al chat de Características (aplicación instantánea)",
    description=(
        "Procesa el mensaje y aplica el cambio inmediatamente sobre la característica "
        "(título, descripción u origen), verificando la consistencia en Requisitos y Modelo. "
        "Si el cambio pertenece a otra fase, devuelve una redirección."
    ),
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Mensaje procesado, modificación aplicada o redirección."},
        status.HTTP_400_BAD_REQUEST: {"description": "Error de validación o tamaño de mensaje."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Token inválido."},
        status.HTTP_404_NOT_FOUND: {"description": "Característica no encontrada."},
        status.HTTP_502_BAD_GATEWAY: {"description": "Error al invocar el LLM."},
    },
)
async def process_feature_chat_message(
    feature_id: str,
    payload: Annotated[SendChatRequest, Body(...)],
    _principal: Annotated[Principal, Depends(get_principal)],
    regen_uc: Annotated[ProcessChatRegenerationUseCase, Depends(_chat_regeneration_uc)],
    validate_uc: Annotated[ValidatePhaseContextUseCase, Depends(_validate_phase_context)],
) -> ChatResponse:
    validation = await validate_uc.execute(
        ValidatePhaseContextInput(
            content=payload.content,
            current_phase=SpecPhase.CARACTERISTICAS,
        )
    )

    if not validation.is_valid:
        return ChatResponse.from_redirect(
            target_phase=validation.target_phase or "",
            redirect_message=validation.redirect_message or "Este cambio no pertenece a la fase de Características.",
        )

    try:
        output = await regen_uc.execute(
            ProcessChatRegenerationInput(
                content=payload.content,
                document_id=feature_id,
                document_type=SpecPhase.CARACTERISTICAS,
                project_id=None,
                context_id=feature_id,
                instance=f"/api/v1/features/{feature_id}/chat",
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (DocumentNotFoundError, FeatureNotFoundError, ProjectNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc
    except LLMInvocationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.problem.detail,
        ) from exc

    return ChatResponse.from_regeneration(output)


@router.get(
    "/history",
    summary="Obtener historial del chat de la característica",
    description="Devuelve todos los mensajes del chat interactivo para una característica específica.",
    response_model=ChatHistoryResponse,
    responses={
        status.HTTP_200_OK: {"description": "Historial obtenido exitosamente."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Token inválido."},
        status.HTTP_404_NOT_FOUND: {"description": "Característica no encontrada."},
    },
)
async def get_feature_chat_history(
    feature_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[GetFeatureChatHistoryUseCase, Depends(_get_feature_chat_history)],
    before: str | None = None,
) -> ChatHistoryResponse:
    try:
        output = await use_case.execute(GetFeatureChatHistoryInput(feature_id=FeatureId(feature_id), before=before))
    except FeatureNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc

    if output.history is None:
        from kosmo.contracts.chat import HistorialChat
        from kosmo.contracts.sdd.document import SpecPhase
        from kosmo.contracts.sdd.ids import ChatHistoryId, ProjectId
        from kosmo.domain.sdd.id_generator import IdGenerator

        empty_history = HistorialChat(
            id=ChatHistoryId(IdGenerator.generate("chat_history")),
            project_id=ProjectId(""),
            phase=SpecPhase.CARACTERISTICAS,
            context_id=feature_id,
        )
        return ChatHistoryResponse.from_domain(empty_history)

    return ChatHistoryResponse.from_domain(output.history)


@router.post(
    "/stream",
    summary="Enviar mensaje al chat de Características con streaming SSE",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Error de validación."},
        status.HTTP_404_NOT_FOUND: {"description": "Característica no encontrada."},
    },
)
async def stream_feature_chat_message(
    feature_id: str,
    payload: Annotated[SendChatRequest, Body(...)],
    _principal: Annotated[Principal, Depends(get_principal)],
    validate_uc: Annotated[ValidatePhaseContextUseCase, Depends(_validate_phase_context)],
    regen_uc: Annotated[ProcessChatRegenerationUseCase, Depends(_chat_regeneration_uc)],
) -> StreamingResponse:
    from kosmo.infrastructure.api.async_generation import sse_regeneration_response

    return await sse_regeneration_response(
        content=payload.content,
        document_id=feature_id,
        document_type=SpecPhase.CARACTERISTICAS,
        pid=None,
        context_id=feature_id,
        regen_uc=regen_uc,
        validate_uc=validate_uc,
    )
