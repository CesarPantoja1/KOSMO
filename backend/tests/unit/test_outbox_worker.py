from __future__ import annotations

import asyncio
from typing import Any

import pytest

from kosmo.infrastructure.persistence.postgres.models import OutboxJobModel
from kosmo.infrastructure.persistence.postgres.outbox import run_outbox_worker


class _MockOutboxStore:
    def __init__(self, jobs: list[OutboxJobModel]) -> None:
        self._pending = list(jobs)
        self.done: list[str] = []
        self.failed: list[tuple[str, str | None]] = []

    async def dequeue(self) -> OutboxJobModel | None:
        if self._pending:
            job = self._pending.pop(0)
            job.status = "processing"
            job.attempts = (job.attempts or 0) + 1
            return job
        return None

    async def mark_done(self, job_id: str) -> None:
        self.done.append(job_id)

    async def mark_failed(self, job_id: str, *, error: str | None = None) -> None:
        self.failed.append((job_id, error))


@pytest.mark.asyncio
@pytest.mark.unit
async def test_outbox_worker_processes_jobs_concurrently() -> None:
    jobs = [
        OutboxJobModel(id=f"job_{i}", job_type="test_task", payload={"idx": i}, attempts=0, status="pending")
        for i in range(4)
    ]
    store = _MockOutboxStore(jobs)

    active_concurrency: list[int] = []
    current_active = 0
    lock = asyncio.Lock()

    async def handler(_job_type: str, _payload: dict[str, Any]) -> None:
        nonlocal current_active
        async with lock:
            current_active += 1
            active_concurrency.append(current_active)
        await asyncio.sleep(0.05)
        async with lock:
            current_active -= 1

    worker_task = asyncio.create_task(
        run_outbox_worker(
            store=store,  # type: ignore[arg-type]
            handler=handler,
            poll_interval=0.01,
            max_concurrency=4,
        )
    )

    for _ in range(50):
        if len(store.done) == 4:
            break
        await asyncio.sleep(0.02)

    worker_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await worker_task

    assert len(store.done) == 4
    assert max(active_concurrency) >= 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_outbox_worker_handles_job_failure() -> None:
    job = OutboxJobModel(id="job_fail", job_type="failing_task", payload={}, attempts=0, status="pending")
    store = _MockOutboxStore([job])

    async def handler(_job_type: str, _payload: dict[str, Any]) -> None:
        raise ValueError("Simulated handler crash")

    worker_task = asyncio.create_task(
        run_outbox_worker(
            store=store,  # type: ignore[arg-type]
            handler=handler,
            poll_interval=0.01,
            max_concurrency=2,
        )
    )

    for _ in range(30):
        if len(store.failed) == 1:
            break
        await asyncio.sleep(0.02)

    worker_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await worker_task

    assert len(store.failed) == 1
    assert store.failed[0][0] == "job_fail"
    assert "ValueError" in (store.failed[0][1] or "")
