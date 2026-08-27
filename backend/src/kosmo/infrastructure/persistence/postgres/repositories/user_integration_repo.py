from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.integrations.github import (
    UserGitHubIntegration,
    UserGitHubIntegrationRepository,
)
from kosmo.contracts.integrations.user_integration import (
    IntegrationProvider,
    UserIntegration,
    UserIntegrationRepository,
)
from kosmo.contracts.sdd.ids import UserId
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.models import UserIntegrationModel


class SqlAlchemyUserIntegrationRepository(UserIntegrationRepository):
    """Adaptador de persistencia PostgreSQL para credenciales y metadatos de integración de usuario."""

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
    def _to_entity(model: UserIntegrationModel) -> UserIntegration:
        try:
            provider = IntegrationProvider(model.provider)
        except ValueError:
            provider = IntegrationProvider.GITHUB

        scopes: list[str] = [str(s) for s in model.scopes]

        return UserIntegration(
            user_id=UserId(model.user_id),
            provider=provider,
            encrypted_access_token=model.access_token_enc,
            account_name=model.account_name,
            encrypted_refresh_token=model.refresh_token_enc,
            scopes=scopes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_by_user_and_provider(
        self,
        user_id: UserId | str,
        provider: IntegrationProvider | str,
    ) -> UserIntegration | None:
        """Obtiene la integración de un usuario con un proveedor específico."""
        user_id_str = str(user_id)
        provider_str = provider.value if isinstance(provider, IntegrationProvider) else str(provider)

        async with self._session_ctx() as session:
            stmt = select(UserIntegrationModel).where(
                UserIntegrationModel.user_id == user_id_str,
                UserIntegrationModel.provider == provider_str,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._to_entity(model)

    async def save(self, integration: UserIntegration) -> UserIntegration:
        """Almacena o actualiza la integración del usuario."""
        user_id_str = str(integration.user_id)
        provider_str = integration.provider.value
        now = datetime.now(UTC)

        async with self._session_ctx() as session:
            stmt = select(UserIntegrationModel).where(
                UserIntegrationModel.user_id == user_id_str,
                UserIntegrationModel.provider == provider_str,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                model = UserIntegrationModel(
                    id=IdGenerator.generate("user_integration"),
                    user_id=user_id_str,
                    provider=provider_str,
                    account_name=integration.account_name,
                    access_token_enc=integration.encrypted_access_token,
                    refresh_token_enc=integration.encrypted_refresh_token,
                    scopes=integration.scopes,
                    created_at=integration.created_at,
                    updated_at=integration.updated_at or now,
                )
                session.add(model)
            else:
                model.account_name = integration.account_name
                model.access_token_enc = integration.encrypted_access_token
                model.refresh_token_enc = integration.encrypted_refresh_token
                model.scopes = integration.scopes
                model.updated_at = integration.updated_at or now

            await self._commit(session)
            return integration

    async def delete(
        self,
        user_id: UserId | str,
        provider: IntegrationProvider | str,
    ) -> bool:
        """Elimina las credenciales de integración del usuario para el proveedor indicado."""
        user_id_str = str(user_id)
        provider_str = provider.value if isinstance(provider, IntegrationProvider) else str(provider)

        async with self._session_ctx() as session:
            stmt = delete(UserIntegrationModel).where(
                UserIntegrationModel.user_id == user_id_str,
                UserIntegrationModel.provider == provider_str,
            )
            result = cast(CursorResult[Any], await session.execute(stmt))
            await self._commit(session)
            return bool(result.rowcount > 0)

    async def list_by_user(self, user_id: UserId | str) -> list[UserIntegration]:
        """Lista todas las integraciones registradas para el usuario."""
        user_id_str = str(user_id)

        async with self._session_ctx() as session:
            stmt = (
                select(UserIntegrationModel)
                .where(UserIntegrationModel.user_id == user_id_str)
                .order_by(UserIntegrationModel.created_at.asc())
            )
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [self._to_entity(m) for m in models]


class SqlAlchemyUserGitHubIntegrationRepository(UserGitHubIntegrationRepository):
    """Adaptador de persistencia PostgreSQL específico para integraciones de GitHub."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._delegate = SqlAlchemyUserIntegrationRepository(
            session_factory=session_factory,
            session=session,
        )

    async def get_by_user_id(self, user_id: UserId) -> UserGitHubIntegration | None:
        """Obtiene la configuración de GitHub asociada a un usuario."""
        integration = await self._delegate.get_by_user_and_provider(
            user_id=user_id,
            provider=IntegrationProvider.GITHUB,
        )
        if integration is None:
            return None
        return UserGitHubIntegration(
            user_id=integration.user_id,
            github_username=integration.account_name or "",
            encrypted_token=integration.encrypted_access_token,
            updated_at=integration.updated_at,
        )

    async def save(self, integration: UserGitHubIntegration) -> None:
        """Persiste la configuración de GitHub del usuario."""
        user_int = UserIntegration(
            user_id=integration.user_id,
            provider=IntegrationProvider.GITHUB,
            encrypted_access_token=integration.encrypted_token,
            account_name=integration.github_username,
            updated_at=integration.updated_at,
        )
        await self._delegate.save(user_int)

    async def delete_by_user_id(self, user_id: UserId) -> bool:
        """Elimina la integración de GitHub del usuario."""
        return await self._delegate.delete(user_id, IntegrationProvider.GITHUB)
