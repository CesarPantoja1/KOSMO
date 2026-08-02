from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from kosmo.application.chat.process_chat_message import (
    ProcessChatMessageInput,
    ProcessChatMessageUseCase,
)
from kosmo.application.chat.validate_phase_context import (
    ValidatePhaseContextInput,
    ValidatePhaseContextUseCase,
)
from kosmo.application.pipeline.kosmo_agent import KOSMOAgent
from kosmo.application.requirements import (
    GetRequirementChatHistoryInput,
    GetRequirementChatHistoryUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.chat import ChatRepository
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import (
    FeatureNotFoundError,
    LLMInvocationError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.domain.pipeline.context_builder import ContextBuilder
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.schemas import (
    ChatHistoryResponse,
    ChatMessage,
    ContextRedirectResponse,
    SendChatRequest,
)

router = APIRouter(
    prefix="/api/v1/features/{feature_id}/requirements/chat",
    tags=["requirements"],
)


def _process_requirement_chat(request: Request) -> ProcessChatMessageUseCase:
    return request.app.state.process_chat_message


def _get_requirement_chat_history(request: Request) -> GetRequirementChatHistoryUseCase:
    return request.app.state.get_requirement_chat_history


def _validate_phase_context(request: Request) -> ValidatePhaseContextUseCase:
    return request.app.state.validate_phase_context


def _context_builder(request: Request) -> ContextBuilder:
    return request.app.state.context_builder


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
    payload: Annotated[SendChatRequest, Body(...)],
    _principal: Annotated[Principal, Depends(get_principal)],
    chat_uc: Annotated[ProcessChatMessageUseCase, Depends(_process_requirement_chat)],
    validate_uc: Annotated[ValidatePhaseContextUseCase, Depends(_validate_phase_context)],
    ctx_builder: Annotated[ContextBuilder, Depends(_context_builder)],
) -> ChatMessage | ContextRedirectResponse:
    fid = FeatureId(feature_id)

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
        context = await ctx_builder.build_requirement_chat_context(fid)
        output = await chat_uc.execute(
            ProcessChatMessageInput(
                project_id=context.feature.project_id,
                phase=SpecPhase.REQUISITOS,
                content=payload.content,
                context=context,
                context_id=str(fid),
                instance=f"/api/v1/features/{feature_id}/requirements/chat",
            )
        )
    except ValueError as exc:
        import structlog
        structlog.get_logger(__name__).error("requirement_chat.value_error", detail=str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (FeatureNotFoundError, ProjectNotFoundError) as exc:
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
    _principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[GetRequirementChatHistoryUseCase, Depends(_get_requirement_chat_history)],
    before: str | None = None,
) -> ChatHistoryResponse:
    try:
        output = await use_case.execute(
            GetRequirementChatHistoryInput(
                feature_id=FeatureId(feature_id),
                before=before,
            )
        )
    except FeatureNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc

    if output.history is None:
        from kosmo.contracts.chat import HistorialChat
        from kosmo.contracts.sdd.ids import ChatHistoryId, ProjectId
        from kosmo.domain.sdd.id_generator import IdGenerator

        empty_history = HistorialChat(
            id=ChatHistoryId(IdGenerator.generate("chat_history")),
            project_id=ProjectId(""),
            phase=SpecPhase.REQUISITOS,
            context_id=feature_id,
        )
        return ChatHistoryResponse.from_domain(empty_history)

    return ChatHistoryResponse.from_domain(output.history)


def _agent_dep(request: Request):
    return request.app.state.agent


def _chat_repo_dep(request: Request) -> ChatRepository:
    return request.app.state.chat_repo  # type: ignore[reportReturnType]


def _suggested_change_dict(sc: object) -> dict[str, object] | None:
    if sc is None:
        return None
    return {
        "id": sc.id,  # type: ignore[reportAttributeAccessIssue]
        "section": sc.section,  # type: ignore[reportAttributeAccessIssue]
        "description": sc.description,  # type: ignore[reportAttributeAccessIssue]
        "diff_before": sc.diff.before,  # type: ignore[reportAttributeAccessIssue]
        "diff_after": sc.diff.after,  # type: ignore[reportAttributeAccessIssue]
        "rationale": sc.rationale,  # type: ignore[reportAttributeAccessIssue]
    }


@router.post(
    "/stream",
    summary="Enviar mensaje al chat de Requisitos con streaming SSE",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Error de validación."},
        status.HTTP_404_NOT_FOUND: {"description": "Característica o requisito no encontrado."},
    },
)
async def stream_requirement_chat_message(
    feature_id: str,
    payload: Annotated[SendChatRequest, Body(...)],
    _principal: Annotated[Principal, Depends(get_principal)],
    validate_uc: Annotated[ValidatePhaseContextUseCase, Depends(_validate_phase_context)],
    ctx_builder: Annotated[ContextBuilder, Depends(_context_builder)],
    agent: Annotated[KOSMOAgent, Depends(_agent_dep)],
    chat_repo: Annotated[ChatRepository, Depends(_chat_repo_dep)],
) -> StreamingResponse:
    from kosmo.infrastructure.api.async_generation import sse_chat_response

    fid = FeatureId(feature_id)
    context = await ctx_builder.build_requirement_chat_context(fid)

    return await sse_chat_response(
        content=payload.content,
        phase=SpecPhase.REQUISITOS,
        skill_name="requirements_chat",
        context=context,
        pid=context.feature.project_id,
        context_id=str(fid),
        chat_repo=chat_repo,
        agent=agent,
        validate_uc=validate_uc,
    )
