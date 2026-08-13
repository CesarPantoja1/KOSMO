from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from kosmo.application.chat.process_chat_modification import (
    ProcessChatModificationInput,
    ProcessChatModificationUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    FeatureNotFoundError,
    LLMInvocationError,
)
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.dependencies.container import get_container
from kosmo.infrastructure.api.schemas import (
    DocumentModifyRequestView,
    DocumentModifyResponseView,
    HttpErrorResponse,
)

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
    responses={
        401: {"model": HttpErrorResponse, "description": "Token ausente, inválido o expirado"},
        404: {"model": HttpErrorResponse, "description": "Documento no encontrado"},
    },
)

_PHASE_MAP: dict[str, SpecPhase] = {
    "discovery": SpecPhase.DESCUBRIMIENTO,
    "features": SpecPhase.CARACTERISTICAS,
    "requirements": SpecPhase.REQUISITOS,
    "model": SpecPhase.MODELO,
}


def _chat_modification_uc(request: Request) -> ProcessChatModificationUseCase:
    return get_container(request).pipeline.process_chat_modification


@router.post(
    "/modify-direct",
    summary="Modificar documento directamente sin fase de plan",
    description=(
        "Recibe una instrucción textual y modifica directamente el documento indicado "
        "sin pasar por la fase de planificación del chat. La IA interpreta la intención, "
        "identifica la sección afectada, aplica el cambio y retorna el documento actualizado "
        "con la sección resaltada."
    ),
    response_model=DocumentModifyResponseView,
    status_code=status.HTTP_200_OK,
)
async def modify_document_direct(
    _principal: Annotated[Principal, Depends(get_principal)],
    body: Annotated[DocumentModifyRequestView, Body(...)],
    uc: Annotated[ProcessChatModificationUseCase, Depends(_chat_modification_uc)],
) -> DocumentModifyResponseView:
    phase = _PHASE_MAP.get(body.document_type)
    if phase is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de documento desconocido: '{body.document_type}'.",
        )

    try:
        output = await uc.execute(
            ProcessChatModificationInput(
                text=body.instruction,
                document_id=body.document_id,
                document_type=phase,
            )
        )
    except (DocumentNotFoundError, FeatureNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc
    except LLMInvocationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.problem.detail,
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not output.success:
        detail_msg = output.clarification_message or "Instrucción ambigua o inválida — se requiere más detalle."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail_msg,
        )

    section_info = f" Sección '{output.modified_section}' modificada." if output.modified_section else ""
    return DocumentModifyResponseView(
        document_id=body.document_id,
        content=output.modified_document or "",
        highlighted_section=output.modified_section,
        message=f"Documento actualizado.{section_info}",
    )
