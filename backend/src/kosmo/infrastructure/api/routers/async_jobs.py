from __future__ import annotations

import asyncio
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from kosmo.contracts.auth import Principal
from kosmo.infrastructure.api.dependencies.auth import get_principal

router = APIRouter(
    prefix="/api/v1/jobs",
    tags=["async-jobs"],
)


@router.get(
    "/{job_id}",
    summary="Consultar estado de un job asíncrono",
)
async def get_job_status(
    job_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Request,
) -> dict[str, Any]:
    store = request.app.state.async_job_store
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job no encontrado")
    return job


@router.get(
    "/{job_id}/stream",
    summary="Stream SSE del progreso de un job asíncrono",
)
async def stream_job(
    job_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Request,
) -> StreamingResponse:
    store = request.app.state.async_job_store

    async def event_stream() -> Any:
        last_status = "pending"
        while True:
            job = await store.get(job_id)
            if job is None:
                yield _sse_event({"type": "error", "detail": "Job no encontrado"})
                return

            if job["status"] != last_status:
                last_status = job["status"]
                yield _sse_event({"type": "status", "status": job["status"]})

            if job["status"] in ("completed", "failed"):
                if job["result"]:
                    yield _sse_event({"type": "result", "data": job["result"]})
                if job["error"]:
                    yield _sse_event({"type": "error", "detail": job["error"]})
                return

            await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),  # type: ignore[reportArgumentType]
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


def _sse_event(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, default=str)}\n\n"
