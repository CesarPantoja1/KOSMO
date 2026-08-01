from __future__ import annotations

import asyncio
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.models import OutboxJobModel

_log = structlog.get_logger(__name__)


class OutboxStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def enqueue(self, job_type: str, payload: dict[str, Any]) -> None:
        model = OutboxJobModel(
            id=IdGenerator.generate("outbox"),
            job_type=job_type,
            payload=payload,
            status="pending",
        )
        async with self._session_factory() as session:
            session.add(model)
            await session.commit()

    async def dequeue(self) -> OutboxJobModel | None:
        async with self._session_factory() as session:
            stmt = (
                select(OutboxJobModel)
                .where(OutboxJobModel.status == "pending")
                .order_by(OutboxJobModel.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            model.status = "processing"
            model.attempts = (model.attempts or 0) + 1
            await session.commit()
            return model

    async def mark_done(self, job_id: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(OutboxJobModel).where(OutboxJobModel.id == job_id).values(status="done")
            )
            await session.commit()

    async def mark_failed(self, job_id: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(OutboxJobModel).where(OutboxJobModel.id == job_id).values(status="failed")
            )
            await session.commit()


async def run_outbox_worker(store: OutboxStore, handler: Any, poll_interval: float = 2.0) -> None:
    while True:
        try:
            job = await store.dequeue()
            if job is not None:
                try:
                    await handler(job.job_type, job.payload)
                    await store.mark_done(job.id)
                except Exception:
                    _log.warning(
                        "outbox.worker_job_failed",
                        job_type=job.job_type,
                        job_id=job.id,
                        exc_info=True,
                    )
                    await store.mark_failed(job.id)
        except Exception:
            _log.warning("outbox.worker_error", exc_info=True)
        await asyncio.sleep(poll_interval)
