from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_, select, update
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.codegen import CodeWorkspace, WorkspaceRepository, WorkspaceStatus
from kosmo.contracts.sdd.ids import ProjectId, WorkspaceId
from kosmo.infrastructure.persistence.postgres.models import WorkspaceModel

# ponytail: umbral de lock stale tras un kill duro del proceso; si un run legítimo
# supera este umbral otro proceso podría robarle el lock — renovar locked_at
# periódicamente si las generaciones llegan a durar más de 30 minutos.
LOCK_STALE_AFTER_MINUTES: int = 30


class SqlAlchemyWorkspaceRepository(WorkspaceRepository):
    """Adaptador de persistencia PostgreSQL para CodeWorkspace."""

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

    @staticmethod
    def _to_entity(model: WorkspaceModel) -> CodeWorkspace:
        return CodeWorkspace(
            id=WorkspaceId(model.id),
            project_id=ProjectId(model.project_id),
            status=WorkspaceStatus.READY if model.path else WorkspaceStatus.NOT_CREATED,
            workspace_dir=model.path if model.path else None,
            current_branch=model.current_branch,
            is_locked=model.is_locked,
            locked_at=model.locked_at,
            locked_by=model.locked_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def by_project_id(self, project_id: ProjectId | str) -> CodeWorkspace | None:
        async with self._session_ctx() as session:
            stmt = select(WorkspaceModel).where(WorkspaceModel.project_id == str(project_id))
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._to_entity(model)

    async def get_by_project_id(self, project_id: ProjectId | str) -> CodeWorkspace | None:
        """Alias para by_project_id."""
        return await self.by_project_id(project_id)

    async def by_id(self, workspace_id: WorkspaceId | str) -> CodeWorkspace | None:
        async with self._session_ctx() as session:
            stmt = select(WorkspaceModel).where(WorkspaceModel.id == str(workspace_id))
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._to_entity(model)

    async def save(self, workspace: CodeWorkspace) -> CodeWorkspace:
        async with self._session_ctx() as session:
            stmt = select(WorkspaceModel).where(WorkspaceModel.project_id == str(workspace.project_id))
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            now = datetime.now(UTC)
            if model is None:
                model = WorkspaceModel(
                    id=str(workspace.id),
                    project_id=str(workspace.project_id),
                    current_branch=workspace.current_branch,
                    is_locked=workspace.is_locked,
                    locked_at=workspace.locked_at,
                    locked_by=workspace.locked_by,
                    path=workspace.workspace_dir or "",
                    created_at=workspace.created_at,
                    updated_at=workspace.updated_at or now,
                )
                session.add(model)
            else:
                model.current_branch = workspace.current_branch
                model.is_locked = workspace.is_locked
                model.locked_at = workspace.locked_at
                model.locked_by = workspace.locked_by
                model.path = workspace.workspace_dir or ""
                model.updated_at = now

            await self._commit(session)
            return workspace

    async def delete(self, project_id: ProjectId | str) -> None:
        async with self._session_ctx() as session:
            stmt = delete(WorkspaceModel).where(WorkspaceModel.project_id == str(project_id))
            await session.execute(stmt)
            await self._commit(session)

    async def update_lock(
        self,
        project_id: ProjectId | str,
        is_locked: bool,
        locked_by: str | None = None,
    ) -> CodeWorkspace | None:
        async with self._session_ctx() as session:
            now = datetime.now(UTC)

            if is_locked:
                # CAS atómico entre procesos: gana quien vea is_locked=false o un lock
                # stale (proceso muerto sin release) según LOCK_STALE_AFTER_MINUTES.
                now = datetime.now(UTC)
                stale_cutoff = now - timedelta(minutes=LOCK_STALE_AFTER_MINUTES)
                cas_stmt = (
                    update(WorkspaceModel)
                    .where(
                        WorkspaceModel.project_id == str(project_id),
                        or_(
                            WorkspaceModel.is_locked.is_(False),
                            WorkspaceModel.locked_at.is_(None),
                            WorkspaceModel.locked_at < stale_cutoff,
                        ),
                    )
                    .values(is_locked=True, locked_at=now, locked_by=locked_by, updated_at=now)
                    .returning(WorkspaceModel)
                )
                result = await session.execute(cas_stmt)
                model = result.scalar_one_or_none()
                if model is not None:
                    await self._commit(session)
                    return self._to_entity(model)

                # Primera adquisición: la fila aún no existe — INSERT bloqueado, un solo proceso gana.
                # El id sigue la convención ws_{project_id} de LocalWorkspaceManager.ensure_workspace.
                insert_stmt = (
                    pg.insert(WorkspaceModel)
                    .values(
                        id=f"ws_{project_id}",
                        project_id=str(project_id),
                        current_branch="main",
                        is_locked=True,
                        locked_at=now,
                        locked_by=locked_by,
                        path="",
                        created_at=now,
                        updated_at=now,
                    )
                    .on_conflict_do_nothing(index_elements=[WorkspaceModel.id])
                    .returning(WorkspaceModel)
                )
                insert_result = await session.execute(insert_stmt)
                inserted = insert_result.scalar_one_or_none()
                await self._commit(session)
                if inserted is None:
                    return None
                return self._to_entity(inserted)

            stmt = select(WorkspaceModel).where(WorkspaceModel.project_id == str(project_id))
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None

            model.is_locked = False
            model.locked_at = None
            model.locked_by = None
            model.updated_at = now

            await self._commit(session)
            return self._to_entity(model)

    async def release_lock(self, project_id: ProjectId | str) -> CodeWorkspace | None:
        return await self.update_lock(project_id, is_locked=False, locked_by=None)
