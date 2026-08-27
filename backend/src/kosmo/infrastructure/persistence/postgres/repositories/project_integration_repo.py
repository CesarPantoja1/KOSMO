from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from ulid import ULID

from kosmo.contracts.integrations.github import (
    CodeSyncLog,
    CodeSyncLogRepository,
    CodeSyncStatus,
    GitHubSyncStatus,
    ProjectGitHubIntegration,
    ProjectGitHubIntegrationRepository,
)
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.models import (
    CodeSyncLogModel,
    ProjectIntegrationModel,
)


class SqlAlchemyProjectGitHubIntegrationRepository(ProjectGitHubIntegrationRepository):
    """Adaptador de persistencia PostgreSQL para metadatos de integración de proyectos con GitHub."""

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
    def _to_entity(model: ProjectIntegrationModel) -> ProjectGitHubIntegration:
        try:
            sync_status = GitHubSyncStatus(model.sync_status)
        except ValueError:
            sync_status = GitHubSyncStatus.NOT_CREATED

        return ProjectGitHubIntegration(
            project_id=ProjectId(model.project_id),
            repo_name=model.repo_name,
            repo_url=model.repo_url or "",
            is_public=model.is_public,
            default_branch=model.default_branch,
            last_push_at=model.last_push_at,
            last_commit_hash=model.last_commit_hash,
            sync_status=sync_status,
            error_message=model.error_message,
            last_synced_at=model.last_push_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_by_project_id(
        self,
        project_id: ProjectId | str,
    ) -> ProjectGitHubIntegration | None:
        """Obtiene los metadatos de integración de GitHub para un proyecto."""
        project_id_str = str(project_id)

        async with self._session_ctx() as session:
            stmt = select(ProjectIntegrationModel).where(
                ProjectIntegrationModel.project_id == project_id_str,
                ProjectIntegrationModel.provider == "github",
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._to_entity(model)

    async def save(
        self,
        integration: ProjectGitHubIntegration,
    ) -> ProjectGitHubIntegration:
        """Almacena o actualiza los metadatos de integración del proyecto con GitHub."""
        project_id_str = str(integration.project_id)
        now = datetime.now(UTC)
        sync_status_str = integration.sync_status.value

        async with self._session_ctx() as session:
            stmt = select(ProjectIntegrationModel).where(
                ProjectIntegrationModel.project_id == project_id_str,
                ProjectIntegrationModel.provider == "github",
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            last_push = integration.last_push_at or integration.last_synced_at

            if model is None:
                model = ProjectIntegrationModel(
                    id=IdGenerator.generate("project_integration"),
                    project_id=project_id_str,
                    provider="github",
                    repo_name=integration.repo_name,
                    repo_url=integration.repo_url,
                    is_public=integration.is_public,
                    default_branch=integration.default_branch,
                    last_push_at=last_push,
                    last_commit_hash=integration.last_commit_hash,
                    sync_status=sync_status_str,
                    error_message=integration.error_message,
                    created_at=integration.created_at,
                    updated_at=integration.updated_at or now,
                )
                session.add(model)
            else:
                model.repo_name = integration.repo_name
                model.repo_url = integration.repo_url
                model.is_public = integration.is_public
                model.default_branch = integration.default_branch
                model.last_push_at = last_push
                model.last_commit_hash = integration.last_commit_hash
                model.sync_status = sync_status_str
                model.error_message = integration.error_message
                model.updated_at = integration.updated_at or now

            await self._commit(session)
            return integration

    async def delete_by_project_id(
        self,
        project_id: ProjectId | str,
    ) -> bool:
        """Elimina los metadatos de integración de GitHub para el proyecto indicado."""
        project_id_str = str(project_id)

        async with self._session_ctx() as session:
            stmt = delete(ProjectIntegrationModel).where(
                ProjectIntegrationModel.project_id == project_id_str,
                ProjectIntegrationModel.provider == "github",
            )
            result = cast(CursorResult[Any], await session.execute(stmt))
            await self._commit(session)
            return bool(result.rowcount > 0)


class SqlAlchemyCodeSyncLogRepository(CodeSyncLogRepository):
    """Adaptador de persistencia PostgreSQL para los registros de auditoría de sincronización de código."""

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
    def _to_entity(model: CodeSyncLogModel) -> CodeSyncLog:
        try:
            status = CodeSyncStatus(model.status)
        except ValueError:
            status = CodeSyncStatus.FAILED

        try:
            log_id = ULID.from_str(model.id)
        except Exception:
            log_id = ULID()

        return CodeSyncLog(
            id=log_id,
            project_id=ProjectId(model.project_id),
            commit_sha=model.commit_sha,
            status=status,
            message=model.message,
            synced_at=model.synced_at,
        )

    async def add_log(self, log: CodeSyncLog) -> None:
        """Registra un nuevo log de sincronización de código."""
        log_id_str = str(log.id) if log.id else IdGenerator.generate("code_sync_log")
        project_id_str = str(log.project_id)
        status_str = log.status.value

        async with self._session_ctx() as session:
            model = CodeSyncLogModel(
                id=log_id_str,
                project_id=project_id_str,
                commit_sha=log.commit_sha,
                status=status_str,
                message=log.message,
                synced_at=log.synced_at,
            )
            session.add(model)
            await self._commit(session)

    async def get_logs_by_project(
        self,
        project_id: ProjectId | str,
    ) -> list[CodeSyncLog]:
        """Obtiene el historial de logs de sincronización de un proyecto ordenado cronológicamente."""
        project_id_str = str(project_id)

        async with self._session_ctx() as session:
            stmt = (
                select(CodeSyncLogModel)
                .where(CodeSyncLogModel.project_id == project_id_str)
                .order_by(CodeSyncLogModel.synced_at.desc())
            )
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [self._to_entity(m) for m in models]
