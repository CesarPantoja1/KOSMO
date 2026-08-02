from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.models import AsyncJobModel


class AsyncJobStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, job_type: str, project_id: str) -> str:
        job_id = IdGenerator.generate("outbox")
        async with self._session_factory() as session:
            session.add(
                AsyncJobModel(
                    id=job_id,
                    job_type=job_type,
                    status="pending",
                    project_id=project_id,
                )
            )
            await session.commit()
        return job_id

    async def update_status(self, job_id: str, status: str, *, result: object = None, error: str = "") -> None:
        async with self._session_factory() as session:
            result_obj = await session.execute(
                select(AsyncJobModel).where(AsyncJobModel.id == job_id).with_for_update()
            )
            model = result_obj.scalar_one_or_none()
            if model is None:
                return
            model.status = status
            model.updated_at = datetime.now(UTC)
            if result is not None:
                if hasattr(result, "model_dump"):
                    model.result_json = result.model_dump(mode="json")  # type: ignore[reportUnknownMemberType]
                elif isinstance(result, dict):
                    model.result_json = result
                else:
                    model.result_json = {"raw": json.dumps(str(result), default=str)}
            if error:
                model.error = error
            await session.commit()

    async def get(self, job_id: str) -> dict | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AsyncJobModel).where(AsyncJobModel.id == job_id)
            )
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return {
                "id": model.id,
                "job_type": model.job_type,
                "status": model.status,
                "project_id": model.project_id,
                "result": model.result_json,
                "error": model.error,
                "created_at": model.created_at.isoformat() if model.created_at else "",
            }
