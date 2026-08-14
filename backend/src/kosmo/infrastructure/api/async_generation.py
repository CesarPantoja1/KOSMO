from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import structlog
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from kosmo.application.chat.validate_phase_context import (
    ValidatePhaseContextInput,
    ValidatePhaseContextOutput,
    ValidatePhaseContextUseCase,
)
from kosmo.contracts.chat import ModificacionChat
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ChatSessionId, ProjectId

if TYPE_CHECKING:
    from kosmo.application.chat.process_chat_message import (
        ProcessChatMessageOutput,
        ProcessChatMessageUseCase,
    )

_log = structlog.get_logger(__name__)


async def validate_chat_content(
    validate_uc: ValidatePhaseContextUseCase,
    content: str,
    document_type: SpecPhase,
) -> ValidatePhaseContextOutput:
    """Valida la fase del mensaje y registra la metrica de la etapa."""
    validate_start = time.monotonic()
    validation = await validate_uc.execute(ValidatePhaseContextInput(content=content, current_phase=document_type))
    _log.info(
        "chat.stage_times",
        phase=document_type.value,
        validate_ms=int((time.monotonic() - validate_start) * 1000),
    )
    return validation


def _modification_dict(modification: ModificacionChat | None) -> dict[str, object] | None:
    if modification is None:
        return None
    return {
        "applied": modification.applied,
        "modified_section": modification.modified_section,
        "change_description": modification.change_description,
        "modified_document": modification.modified_document,
        "before": modification.before,
        "after": modification.after,
        "undo_version_id": None,
        "clarification_message": modification.clarification_message,
    }


def _message_dict(output: ProcessChatMessageOutput) -> dict[str, object]:
    msg = output.message
    return {
        "type": "message",
        "id": str(msg.id),
        "role": "assistant",
        "content": msg.content,
        "suggestions": [
            {
                "id": sc.id,
                "section": sc.section,
                "description": sc.description,
                "diff_before": sc.diff.before,
                "diff_after": sc.diff.after,
                "rationale": sc.rationale,
                "applied": sc.applied,
                "not_applied_reason": sc.not_applied_reason,
            }
            for sc in msg.suggested_changes
        ],
        "modification": _modification_dict(msg.modification),
        "consistency": None,
        "timestamp": msg.timestamp.isoformat(),
    }


async def sse_chat_response(
    content: str,
    document_type: SpecPhase,
    pid: ProjectId,
    context_id: str | None,
    context: object,
    chat_uc: ProcessChatMessageUseCase,
    validate_uc: ValidatePhaseContextUseCase,
    session_id: ChatSessionId | None = None,
) -> StreamingResponse:
    """Streaming real del chat: tokens conforme se generan y evento final con las cards."""
    from kosmo.application.chat.process_chat_message import (
        ChatStreamChunk,
        ProcessChatMessageInput,
    )

    validation = await validate_chat_content(validate_uc, content, document_type)
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation.redirect_message or "Mensaje fuera de fase",
        )

    input_data = ProcessChatMessageInput(
        content=content,
        project_id=pid,
        phase=document_type,
        context=context,
        context_id=context_id,
        session_id=session_id,
    )

    async def event_stream() -> AsyncGenerator[str]:
        yield "data: " + json.dumps({"type": "start"}, ensure_ascii=False) + "\n\n"
        async for item in chat_uc.execute_stream(input_data):
            if isinstance(item, ChatStreamChunk):
                yield (
                    "data: "
                    + json.dumps(
                        {"type": "chunk", "content": item.content},
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )
            else:
                yield "data: " + json.dumps(_message_dict(item), ensure_ascii=False) + "\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


async def sse_consistency_response(
    generator: AsyncGenerator[str],
) -> StreamingResponse:
    async def event_stream() -> AsyncGenerator[str]:
        async for chunk in generator:
            yield chunk

    return StreamingResponse(
        event_stream(),  # type: ignore[reportArgumentType]
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
