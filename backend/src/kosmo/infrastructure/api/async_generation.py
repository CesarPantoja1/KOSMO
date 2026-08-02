from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from kosmo.contracts.chat import ChatRepository, ChatRole, MensajeChat, SugerenciaCambio
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ChatMessageId, ProjectId
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.async_job_store import AsyncJobStore

_log = structlog.get_logger(__name__)


async def _run_generation_job(
    job_store: AsyncJobStore,
    job_id: str,
    coro: Any,
) -> None:
    try:
        await job_store.update_status(job_id, "processing")
        result = await coro
        await job_store.update_status(job_id, "completed", result=result)
    except Exception as exc:
        _log.warning("async_job.failed", job_id=job_id, exc_info=True)
        await job_store.update_status(job_id, "failed", error=str(exc))


async def launch_async(
    job_store: AsyncJobStore,
    job_type: str,
    project_id: str,
    coro: Any,
) -> str:
    job_id = await job_store.create(job_type=job_type, project_id=project_id)
    asyncio.create_task(_run_generation_job(job_store, job_id, coro))
    return job_id


def _suggested_change_dict(sc: SugerenciaCambio | None) -> dict[str, Any] | None:
    if not sc:
        return None
    return {
        "section": sc.section,
        "description": sc.description,
        "diff": {"before": sc.diff.before, "after": sc.diff.after},
        "rationale": sc.rationale,
    }


async def sse_chat_response(
    content: str,
    phase: SpecPhase,
    skill_name: str,
    context: Any,
    pid: ProjectId,
    context_id: str | None,
    chat_repo: ChatRepository,
    agent: Any,
    validate_uc: Any,
) -> StreamingResponse:
    from kosmo.application.chat.validate_phase_context import (
        ValidatePhaseContextInput,
    )

    validation = await validate_uc.execute(
        ValidatePhaseContextInput(content=content, current_phase=phase)
    )
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation.redirect_message or "Mensaje fuera de fase",
        )

    history = await chat_repo.get_history(pid, phase, context_id=context_id)
    prior_messages = list(history.messages) if history else []

    user_msg = MensajeChat(
        id=ChatMessageId(IdGenerator.generate("chat_message")),
        role=ChatRole.USER,
        content=content,
    )
    await chat_repo.save_message(pid, phase, user_msg, context_id=context_id)

    messages = prior_messages + [user_msg]

    async def event_stream() -> Any:
        try:
            async for chunk in agent.execute_conversation_stream(
                skill_name=skill_name,
                messages=messages,
                context=context,
                project_id=pid,
            ):
                if isinstance(chunk, MensajeChat):
                    await chat_repo.save_message(pid, phase, chunk, context_id=context_id)
                    msg_data = {
                        "type": "message",
                        "id": str(chunk.id),
                        "role": "assistant",
                        "content": chunk.content,
                        "suggested_change": _suggested_change_dict(chunk.suggested_change),
                        "timestamp": chunk.timestamp.isoformat(),
                    }
                    yield f"data: {json.dumps(msg_data, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk}, ensure_ascii=False)}\n\n"
        except Exception:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Error interno'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
