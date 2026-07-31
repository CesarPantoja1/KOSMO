from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from kosmo.application.chat.validate_phase_context import (
    ValidatePhaseContextInput,
    ValidatePhaseContextUseCase,
)
from kosmo.application.requirements import (
    GetRequirementChatHistoryInput,
    GetRequirementChatHistoryUseCase,
    ProcessRequirementChatMessageInput,
    ProcessRequirementChatMessageUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import (
    FeatureNotFoundError,
    LLMInvocationError,
)
from kosmo.contracts.sdd.ids import FeatureId, RequirementId
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.schemas import (
    ChatHistoryResponse,
    ChatMessage,
    ContextRedirectResponse,
    SendChatRequest,
)

router = APIRouter(
    prefix="/api/v1/features/{feature_id}/requirements/{requirement_id}/chat",
    tags=["requirements"],
)


def _process_requirement_chat(request: Request) -> ProcessRequirementChatMessageUseCase:
    return request.app.state.process_requirement_chat_message


def _get_requirement_chat_history(request: Request) -> GetRequirementChatHistoryUseCase:
    return request.app.state.get_requirement_chat_history


def _validate_phase_context(request: Request) -> ValidatePhaseContextUseCase:
    return request.app.state.validate_phase_context


@router.post(
    "",
    summary="Enviar mensaje al chat de Requisitos",
    description=(
        "Procesa un mensaje del usuario en el contexto de un requisito "
        "específico, validando que la solicitud corresponda al ámbito de la fase. "
        "Si el mensaje corresponde a otra fase, devuelve una redirección."
    ),
    response_model=ChatMessage | ContextRedirectResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Mensaje procesado o redirección."},
        status.HTTP_400_BAD_REQUEST: {"description": "Error de validación o tamaño de mensaje."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Token inválido."},
        status.HTTP_404_NOT_FOUND: {"description": "Característica o requisito no encontrado."},
        status.HTTP_502_BAD_GATEWAY: {"description": "Error al invocar el LLM."},
    },
)
async def process_requirement_chat_message(
    feature_id: str,
    requirement_id: str,
    payload: Annotated[SendChatRequest, Body(...)],
    _principal: Annotated[Principal, Depends(get_principal)],
    chat_uc: Annotated[ProcessRequirementChatMessageUseCase, Depends(_process_requirement_chat)],
    validate_uc: Annotated[ValidatePhaseContextUseCase, Depends(_validate_phase_context)],
) -> ChatMessage | ContextRedirectResponse:
    fid = FeatureId(feature_id)
    rid = RequirementId(requirement_id)

    validation = await validate_uc.execute(
        ValidatePhaseContextInput(
            content=payload.content,
            current_phase=SpecPhase.REQUISITOS,
        )
    )

    if not validation.is_valid:
        return ContextRedirectResponse(
            message=validation.redirect_message or "Este cambio no pertenece a la fase de Requisitos.",
            target_phase=validation.target_phase or "",
        )

    try:
        output = await chat_uc.execute(
            ProcessRequirementChatMessageInput(
                feature_id=fid,
                requirement_id=rid,
                content=payload.content,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except FeatureNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc
    except LLMInvocationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.problem.detail,
        ) from exc

    return ChatMessage.from_domain(output.message)


@router.get(
    "/history",
    summary="Obtener historial del chat de un requisito",
    description="Devuelve todos los mensajes del chat interactivo para un requisito específico.",
    response_model=ChatHistoryResponse,
    responses={
        status.HTTP_200_OK: {"description": "Historial obtenido exitosamente."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Token inválido."},
        status.HTTP_404_NOT_FOUND: {"description": "Característica no encontrada."},
    },
)
async def get_requirement_chat_history(
    feature_id: str,
    requirement_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[GetRequirementChatHistoryUseCase, Depends(_get_requirement_chat_history)],
) -> ChatHistoryResponse:
    try:
        output = await use_case.execute(
            GetRequirementChatHistoryInput(
                feature_id=FeatureId(feature_id),
                requirement_id=RequirementId(requirement_id),
            )
        )
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
            phase=SpecPhase.REQUISITOS,
            context_id=requirement_id,
        )
        return ChatHistoryResponse.from_domain(empty_history)

    return ChatHistoryResponse.from_domain(output.history)
