from __future__ import annotations

import asyncio
from typing import Any

import structlog

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
