from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.ai.ai_config import (
    DEFAULT_AI_PROVIDER,
    AIProvider,
    UserAiConfig,
    UserAiConfigRepository,
)
from kosmo.contracts.auth.secrets import EncryptedSecret
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.models import UserAiConfigModel


class SqlAlchemyUserAiConfigRepository(UserAiConfigRepository):
    """Adaptador de persistencia PostgreSQL para la configuración de Inteligencia Artificial del usuario."""

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
    def _to_entity(model: UserAiConfigModel) -> UserAiConfig:
        encrypted_key: EncryptedSecret | None = None
        if model.encrypted_api_key is not None and model.encrypted_api_key.strip():
            encrypted_key = EncryptedSecret(ciphertext=model.encrypted_api_key.strip().encode("utf-8"))

        try:
            provider = AIProvider(model.provider)
        except ValueError:
            provider = DEFAULT_AI_PROVIDER

        return UserAiConfig(
            user_id=model.user_id,
            provider=provider,
            model=model.model,
            encrypted_api_key=encrypted_key,
            is_custom=model.is_custom,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def by_user_id(self, user_id: str) -> UserAiConfig | None:
        """Obtiene la configuración de IA asociada a un usuario."""
        async with self._session_ctx() as session:
            stmt = select(UserAiConfigModel).where(UserAiConfigModel.user_id == user_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._to_entity(model)

    async def save(self, config: UserAiConfig) -> UserAiConfig:
        """Persiste o actualiza la configuración de IA de un usuario."""
        async with self._session_ctx() as session:
            stmt = select(UserAiConfigModel).where(UserAiConfigModel.user_id == config.user_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            raw_enc_key: str | None = None
            if isinstance(config.encrypted_api_key, EncryptedSecret):
                raw_enc_key = config.encrypted_api_key.ciphertext.decode("utf-8")
            elif isinstance(config.encrypted_api_key, bytes):
                raw_enc_key = config.encrypted_api_key.decode("utf-8")

            provider_val = config.provider.value
            now = datetime.now(UTC)

            if model is None:
                model = UserAiConfigModel(
                    id=IdGenerator.generate("ai_config"),
                    user_id=config.user_id,
                    provider=provider_val,
                    model=config.model,
                    encrypted_api_key=raw_enc_key,
                    is_custom=config.is_custom,
                    created_at=config.created_at,
                    updated_at=config.updated_at or now,
                )
                session.add(model)
            else:
                model.provider = provider_val
                model.model = config.model
                model.encrypted_api_key = raw_enc_key
                model.is_custom = config.is_custom
                model.updated_at = config.updated_at or now

            await self._commit(session)
            return config

    async def delete(self, user_id: str) -> None:
        """Elimina la configuración de IA personalizada del usuario."""
        async with self._session_ctx() as session:
            stmt = delete(UserAiConfigModel).where(UserAiConfigModel.user_id == user_id)
            await session.execute(stmt)
            await self._commit(session)
