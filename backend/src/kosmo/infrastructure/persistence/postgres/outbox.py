from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.models import OutboxJobModel

_log = structlog.get_logger(__name__)

_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = 5.0


class OutboxStore:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        if session_factory is None and session is None:
            raise ValueError("Se requiere session_factory o session")
        self._session_factory = session_factory
        self._session = session

    @asynccontextmanager
    async def _session_ctx(self) -> AsyncGenerator[AsyncSession]:
        if self._session is not None:
            yield self._session
            return
        assert self._session_factory is not None
        async with self._session_factory() as session:
            yield session

    async def _commit(self, session: AsyncSession) -> None:
        if self._session is None:
            await session.commit()

    async def enqueue(self, job_type: str, payload: dict[str, Any]) -> None:
        model = OutboxJobModel(
            id=IdGenerator.generate("outbox"),
            job_type=job_type,
            payload=payload,
            status="pending",
        )
        async with self._session_ctx() as session:
            session.add(model)
            await self._commit(session)

    async def dequeue(self) -> OutboxJobModel | None:
        assert self._session_factory is not None
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
        assert self._session_factory is not None
        async with self._session_factory() as session:
            await session.execute(update(OutboxJobModel).where(OutboxJobModel.id == job_id).values(status="done"))
            await session.commit()

    async def mark_failed(self, job_id: str, *, error: str | None = None) -> None:
        assert self._session_factory is not None
        async with self._session_factory() as session:
            stmt = select(OutboxJobModel).where(OutboxJobModel.id == job_id).with_for_update()
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return
            current_attempts = model.attempts or 0
            if current_attempts >= _MAX_ATTEMPTS:
                model.status = "dead"
            else:
                model.status = "failed"
            if error:
                model.last_error = error[:1000]  # truncate for safety
            await session.commit()


async def run_outbox_worker(
    store: OutboxStore,
    handler: Any,
    poll_interval: float = 2.0,
    *,
    max_attempts: int = _MAX_ATTEMPTS,
    backoff_seconds: float = _BACKOFF_SECONDS,
) -> None:
    fail_timestamps: list[float] = []

    while True:
        try:
            job = await store.dequeue()
            if job is not None:
                try:
                    await handler(job.job_type, job.payload)
                    await store.mark_done(job.id)
                except Exception as exc:
                    error_msg = f"{type(exc).__name__}: {exc!s}"[:500]
                    _log.warning(
                        "outbox.worker_job_failed",
                        job_type=job.job_type,
                        job_id=job.id,
                        attempts=job.attempts,
                        exc_info=True,
                    )
                    await store.mark_failed(job.id, error=error_msg)

                    if job.attempts < max_attempts:
                        fail_timestamps.append(asyncio.get_event_loop().time())
                        # Remove timestamps older than the backoff window
                        now = asyncio.get_event_loop().time()
                        fail_timestamps = [t for t in fail_timestamps if now - t < backoff_seconds]
                        if len(fail_timestamps) >= 3:
                            _log.info("outbox.backoff_applied", delay=backoff_seconds)
                            await asyncio.sleep(backoff_seconds)
                            fail_timestamps.clear()
        except Exception:
            _log.warning("outbox.worker_error", exc_info=True)
        await asyncio.sleep(poll_interval)
