from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from kosmo.application.discovery import (
    GenerateDiscoveryInput,
    GenerateDiscoveryUseCase,
    GetDiscoveryInput,
    GetDiscoveryUseCase,
    RefineDiscoveryInput,
    RefineDiscoveryUseCase,
    SaveDiscoveryInput,
    SaveDiscoveryUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    LLMInvocationError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.schemas import DiscoveryResponse, RefineDiscoveryRequest

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/discovery",
    tags=["discovery"],
)


def _generate_discovery(request: Request) -> GenerateDiscoveryUseCase:
    return request.app.state.generate_discovery


def _get_discovery(request: Request) -> GetDiscoveryUseCase:
    return request.app.state.get_discovery


def _save_discovery(request: Request) -> SaveDiscoveryUseCase:
    return request.app.state.save_discovery


def _refine_discovery(request: Request) -> RefineDiscoveryUseCase:
    return request.app.state.refine_discovery


@router.post(
    "",
    summary="Generar documento de descubrimiento con IA",
    description=(
        "Genera el documento de visión de producto para un proyecto "
        "utilizando inteligencia artificial. El documento se estructura "
        "en 7 secciones obligatorias siguiendo el formato de descubrimiento KOSMO. "
        "Requiere autenticación mediante Bearer token."
    ),
    response_model=DiscoveryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "description": "Documento de descubrimiento generado exitosamente.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Token de acceso inválido o ausente.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Proyecto no encontrado.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "description": "Error al invocar el servicio de IA.",
        },
    },
)
async def generate_discovery(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[GenerateDiscoveryUseCase, Depends(_generate_discovery)],
) -> DiscoveryResponse:
    try:
        output = await use_case.execute(GenerateDiscoveryInput(project_id=ProjectId(project_id)))
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
