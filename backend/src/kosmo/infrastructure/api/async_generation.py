from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from kosmo.contracts.chat import ModificacionChat
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId


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


async def sse_regeneration_response(
    content: str,
    document_id: str,
    document_type: SpecPhase,
    pid: ProjectId | None,
    context_id: str | None,
    regen_uc: Any,
    validate_uc: Any,
) -> StreamingResponse:
    from kosmo.application.chat.process_chat_regeneration import ProcessChatRegenerationInput
    from kosmo.application.chat.validate_phase_context import (
        ValidatePhaseContextInput,
    )

    validation = await validate_uc.execute(ValidatePhaseContextInput(content=content, current_phase=document_type))
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation.redirect_message or "Mensaje fuera de fase",
        )

    output = await regen_uc.execute(
        ProcessChatRegenerationInput(
            content=content,
            document_id=document_id,
            document_type=document_type,
            project_id=pid,
            context_id=context_id,
        )
    )

    msg = output.message
    msg_data = {
        "type": "message",
        "id": str(msg.id),
        "role": "assistant",
        "content": msg.content,
        "modification": _modification_dict(output.modification),
        "consistency": output.downstream_impact,
        "timestamp": msg.timestamp.isoformat(),
    }

    async def event_stream() -> AsyncGenerator[str]:
        yield f"data: {json.dumps(msg_data, ensure_ascii=False)}\n\n"

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
