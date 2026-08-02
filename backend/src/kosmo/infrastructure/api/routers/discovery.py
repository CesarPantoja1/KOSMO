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
from kosmo.application.discovery import (
    GenerateDiscoveryInput,
    GenerateDiscoveryUseCase,
    GetDiscoveryChatHistoryInput,
    GetDiscoveryChatHistoryUseCase,
    GetDiscoveryInput,
    GetDiscoveryUseCase,
    RefineDiscoveryInput,
    RefineDiscoveryUseCase,
    SaveDiscoveryInput,
    SaveDiscoveryUseCase,
)
from kosmo.application.pipeline.kosmo_agent import KOSMOAgent
from kosmo.contracts.auth import Principal
from kosmo.contracts.chat import ChatRepository
from kosmo.contracts.sdd.document import RichTextDocument, SpecPhase
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    LLMInvocationError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.pipeline.context_builder import ContextBuilder
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.dependencies.rate_limit import ProjectGenerationRateLimiter
from kosmo.infrastructure.api.schemas import (
    ChatHistoryResponse,
    ChatMessage,
    ContextRedirectResponse,
    DiscoveryResponse,
    RefineDiscoveryRequest,
    SendChatRequest,
)

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/discovery",
    tags=["discovery"],
)

_generation_rate_limiter = ProjectGenerationRateLimiter(requests_per_hour=20)


def _generate_discovery(request: Request) -> GenerateDiscoveryUseCase:
    return request.app.state.generate_discovery


def _get_discovery(request: Request) -> GetDiscoveryUseCase:
    return request.app.state.get_discovery


def _save_discovery(request: Request) -> SaveDiscoveryUseCase:
    return request.app.state.save_discovery


def _refine_discovery(request: Request) -> RefineDiscoveryUseCase:
    return request.app.state.refine_discovery


def _process_discovery_chat(request: Request) -> ProcessChatMessageUseCase:
    return request.app.state.process_chat_message


def _context_builder(request: Request) -> ContextBuilder:
    return request.app.state.context_builder


def _validate_phase_context(request: Request) -> ValidatePhaseContextUseCase:
    return request.app.state.validate_phase_context


def _get_discovery_chat_history(request: Request) -> GetDiscoveryChatHistoryUseCase:
    return request.app.state.get_discovery_chat_history


@router.post(
    "",
    summary="Generar documento de descubrimiento con IA (asíncrono)",
    description=(
        "Genera el documento de visión de producto para un proyecto "
        "utilizando inteligencia artificial. Devuelve un job_id para seguir el progreso "
        "via GET /api/v1/jobs/{job_id} o SSE en /api/v1/jobs/{job_id}/stream."
    ),
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_202_ACCEPTED: {"description": "Job de generación creado exitosamente."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Token de acceso inválido o ausente."},
    },
)
async def generate_discovery(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    _rate: Annotated[None, Depends(_generation_rate_limiter)],
    use_case: Annotated[GenerateDiscoveryUseCase, Depends(_generate_discovery)],
    request: Request,
) -> dict[str, str]:
    from kosmo.infrastructure.api.async_generation import launch_async

    job_id = await launch_async(
        request.app.state.async_job_store,
        "discovery_generate",
        project_id,
        use_case.execute(GenerateDiscoveryInput(project_id=ProjectId(project_id))),
    )
    return {"job_id": job_id}


@router.get(
    "",
    summary="Obtener documento de descubrimiento",
    description=(
        "Devuelve el documento de descubrimiento almacenado de un proyecto. "
        "Requiere autenticación mediante Bearer token."
    ),
    response_model=DiscoveryResponse,
    responses={
        status.HTTP_200_OK: {
            "description": "Documento de descubrimiento del proyecto.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Token de acceso inválido o ausente.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Documento de descubrimiento no encontrado.",
        },
    },
)
async def get_discovery(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[GetDiscoveryUseCase, Depends(_get_discovery)],
) -> DiscoveryResponse:
    try:
        output = await use_case.execute(GetDiscoveryInput(project_id=ProjectId(project_id)))
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc
    return DiscoveryResponse(
        id=str(output.project_id),
        project_id=str(output.project_id),
        content=_document_to_markdown(output.document),
    )


@router.put(
    "",
    summary="Guardar documento de descubrimiento",
    description=(
        "Persiste manualmente un documento de descubrimiento para un proyecto. "
        "Permite guardar o reemplazar el documento sin invocar al agente de IA. "
        "Requiere autenticación mediante Bearer token."
    ),
    response_model=DiscoveryResponse,
    responses={
        status.HTTP_200_OK: {
            "description": "Documento de descubrimiento guardado exitosamente.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Token de acceso inválido o ausente.",
        },
    },
)
async def save_discovery(
    project_id: str,
    payload: Annotated[dict[str, str], Body(...)],
    _principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[SaveDiscoveryUseCase, Depends(_save_discovery)],
) -> DiscoveryResponse:
    document = _markdown_to_document(payload.get("content", ""))
    output = await use_case.execute(
        SaveDiscoveryInput(
            project_id=ProjectId(project_id),
            document=document,
        )
    )
    return DiscoveryResponse(
        id=str(output.project_id),
        project_id=str(output.project_id),
        content=payload.get("content", ""),
    )


@router.post(
    "/refine",
    summary="Refinar documento de descubrimiento con IA",
    description=(
        "Refina el documento de descubrimiento de un proyecto aplicando las "
        "instrucciones proporcionadas por el usuario mediante inteligencia artificial. "
        "El documento actual se conserva intacto si la IA falla. "
        "Las instrucciones no pueden exceder los 500 caracteres. "
        "Requiere autenticación mediante Bearer token."
    ),
    response_model=DiscoveryResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Documento de descubrimiento refinado exitosamente.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Las instrucciones exceden los 500 caracteres.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Token de acceso inválido o ausente.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Proyecto no encontrado o sin documento de descubrimiento previo.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "description": "Error al invocar el servicio de IA.",
        },
    },
)
async def refine_discovery(
    project_id: str,
    payload: Annotated[RefineDiscoveryRequest, Body(...)],
    _principal: Annotated[Principal, Depends(get_principal)],
    _rate: Annotated[None, Depends(_generation_rate_limiter)],
    use_case: Annotated[RefineDiscoveryUseCase, Depends(_refine_discovery)],
) -> DiscoveryResponse:
    try:
        output = await use_case.execute(
            RefineDiscoveryInput(
                project_id=ProjectId(project_id),
                instructions=payload.instructions,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc
    except LLMInvocationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.problem.detail,
        ) from exc
    return DiscoveryResponse(
        id=str(output.project_id),
        project_id=str(output.project_id),
        content=_document_to_markdown(output.document),
    )


def _document_to_markdown(doc: RichTextDocument) -> str:
    from kosmo.domain.sdd.document_converters import document_to_markdown

    return document_to_markdown(doc)


def _markdown_to_document(content: str) -> RichTextDocument:
    from kosmo.domain.sdd.document_converters import markdown_to_document

    return markdown_to_document(content)


@router.post(
    "/chat",
    summary="Enviar mensaje al chat de Descubrimiento",
    description=(
        "Procesa un mensaje del usuario en el contexto de Descubrimiento, validando que "
        "la solicitud corresponda al ámbito de la fase. Si el mensaje corresponde a otra "
        "fase, devuelve una redirección."
    ),
    response_model=ChatMessage | ContextRedirectResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Mensaje procesado o redirección."},
        status.HTTP_400_BAD_REQUEST: {"description": "Error de validación o tamaño de mensaje."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Token inválido."},
        status.HTTP_404_NOT_FOUND: {"description": "Proyecto no encontrado."},
        status.HTTP_502_BAD_GATEWAY: {"description": "Error al invocar el LLM."},
    },
)
async def process_chat_message(
    project_id: str,
    payload: Annotated[SendChatRequest, Body(...)],
    _principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[ProcessChatMessageUseCase, Depends(_process_discovery_chat)],
    ctx_builder: Annotated[ContextBuilder, Depends(_context_builder)],
    validate_uc: Annotated[ValidatePhaseContextUseCase, Depends(_validate_phase_context)],
) -> ChatMessage | ContextRedirectResponse:
    validation = await validate_uc.execute(
        ValidatePhaseContextInput(
            content=payload.content,
            current_phase=SpecPhase.DESCUBRIMIENTO,
        )
    )

    if not validation.is_valid:
        return ContextRedirectResponse(
            message=validation.redirect_message or "Este cambio no pertenece a la fase de Descubrimiento.",
            target_phase=validation.target_phase or "",
        )

    try:
        context = await ctx_builder.build_discovery_chat_context(ProjectId(project_id))
        output = await use_case.execute(
            ProcessChatMessageInput(
                project_id=ProjectId(project_id),
                phase=SpecPhase.DESCUBRIMIENTO,
                content=payload.content,
                context=context,
                instance=f"/api/v1/projects/{project_id}/discovery/chat",
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ProjectNotFoundError as exc:
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
    "/chat",
    summary="Obtener historial de chat de Descubrimiento",
    description="Devuelve todos los mensajes del chat interactivo para la fase de Descubrimiento.",
    response_model=ChatHistoryResponse,
    responses={
        status.HTTP_200_OK: {"description": "Historial obtenido exitosamente."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Token inválido."},
        status.HTTP_404_NOT_FOUND: {"description": "Proyecto no encontrado."},
    },
)
async def get_chat_history(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[GetDiscoveryChatHistoryUseCase, Depends(_get_discovery_chat_history)],
    before: str | None = None,
) -> ChatHistoryResponse:
    try:
        output = await use_case.execute(
            GetDiscoveryChatHistoryInput(project_id=ProjectId(project_id), before=before)
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc

    if output.history is None:
        from kosmo.contracts.chat import HistorialChat
        from kosmo.contracts.sdd.document import SpecPhase
        from kosmo.contracts.sdd.ids import ChatHistoryId
        from kosmo.domain.sdd.id_generator import IdGenerator

        empty_history = HistorialChat(
            id=ChatHistoryId(IdGenerator.generate("chat_history")),
            project_id=ProjectId(project_id),
            phase=SpecPhase.DESCUBRIMIENTO,
        )
        return ChatHistoryResponse.from_domain(empty_history)

    return ChatHistoryResponse.from_domain(output.history)


def _agent_dep(request: Request) -> KOSMOAgent:
    return request.app.state.agent


def _chat_repo_dep(request: Request) -> ChatRepository:
    return request.app.state.chat_repo

@router.post(
    "/chat/stream",
    summary="Enviar mensaje al chat de Descubrimiento con streaming SSE",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Error de validación."},
        status.HTTP_404_NOT_FOUND: {"description": "Proyecto no encontrado."},
    },
)
async def stream_chat_message(
    project_id: str,
    payload: Annotated[SendChatRequest, Body(...)],
    _principal: Annotated[Principal, Depends(get_principal)],
    validate_uc: Annotated[ValidatePhaseContextUseCase, Depends(_validate_phase_context)],
    ctx_builder: Annotated[ContextBuilder, Depends(_context_builder)],
    agent: Annotated[KOSMOAgent, Depends(_agent_dep)],
    chat_repo: Annotated[ChatRepository, Depends(_chat_repo_dep)],
) -> StreamingResponse:
    from kosmo.infrastructure.api.async_generation import sse_chat_response

    pid = ProjectId(project_id)
    context = await ctx_builder.build_discovery_chat_context(pid)

    return await sse_chat_response(
        content=payload.content,
        phase=SpecPhase.DESCUBRIMIENTO,
        skill_name="discovery_chat",
        context=context,
        pid=pid,
        context_id=None,
        chat_repo=chat_repo,
        agent=agent,
        validate_uc=validate_uc,
    )
