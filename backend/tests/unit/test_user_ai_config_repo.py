from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.ai.ai_config import (
    DEFAULT_AI_MODEL,
    DEFAULT_AI_PROVIDER,
    AIProvider,
    UserAiConfig,
    UserAiConfigRepository,
)
from kosmo.contracts.auth.secrets import EncryptedSecret
from kosmo.infrastructure.persistence.postgres.models import UserAiConfigModel
from kosmo.infrastructure.persistence.postgres.repositories.user_ai_config_repo import (
    SqlAlchemyUserAiConfigRepository,
)


def _make_config(
    user_id: str = "usr_01",
    provider: AIProvider = AIProvider.OPENAI,
    model: str = "gpt-4o",
    encrypted_api_key: EncryptedSecret | bytes | None = None,
    is_custom: bool = True,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> UserAiConfig:
    now = datetime.now(UTC)
    return UserAiConfig(
        user_id=user_id,
        provider=provider,
        model=model,
        encrypted_api_key=encrypted_api_key,
        is_custom=is_custom,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


def _make_async_session_mock(returned_model: UserAiConfigModel | None = None) -> MagicMock:
    mock_session = MagicMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = returned_model
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()
    return mock_session


@pytest.mark.unit
@pytest.mark.asyncio
async def test_init_raises_without_session_or_factory() -> None:
    # Arrange & Act & Assert
    with pytest.raises(ValueError, match="Se requiere session_factory o session"):
        SqlAlchemyUserAiConfigRepository(session_factory=None, session=None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_inserts_new_user_ai_config_when_none_exists() -> None:
    # Arrange
    secret = EncryptedSecret(ciphertext=b"encrypted_sk_openai")
    config = _make_config(
        user_id="usr_01",
        provider=AIProvider.OPENAI,
        model="gpt-4o",
        encrypted_api_key=secret,
        is_custom=True,
    )
    mock_session = _make_async_session_mock(returned_model=None)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserAiConfigRepository(session_factory=mock_session_factory)

    # Act
    result = await repo.save(config)

    # Assert
    assert result == config
    mock_session.add.assert_called_once()
    added_model = mock_session.add.call_args[0][0]
    assert added_model.user_id == "usr_01"
    assert added_model.provider == "openai"
    assert added_model.model == "gpt-4o"
    assert added_model.encrypted_api_key == "encrypted_sk_openai"
    assert added_model.is_custom is True
    mock_session.commit.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_updates_existing_user_ai_config() -> None:
    # Arrange
    now = datetime.now(UTC)
    new_secret = EncryptedSecret(ciphertext=b"new_encrypted_key")
    updated_config = _make_config(
        user_id="usr_01",
        provider=AIProvider.ANTHROPIC,
        model="claude-3-5-sonnet-20241022",
        encrypted_api_key=new_secret,
        is_custom=True,
    )
    existing_model = UserAiConfigModel(
        id="uai_01",
        user_id="usr_01",
        provider="openai",
        model="gpt-4o",
        encrypted_api_key="old_encrypted_key",
        is_custom=True,
        created_at=now,
        updated_at=now,
    )
    mock_session = _make_async_session_mock(returned_model=existing_model)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserAiConfigRepository(session_factory=mock_session_factory)

    # Act
    result = await repo.save(updated_config)

    # Assert
    assert result == updated_config
    assert existing_model.provider == "anthropic"
    assert existing_model.model == "claude-3-5-sonnet-20241022"
    assert existing_model.encrypted_api_key == "new_encrypted_key"
    assert existing_model.is_custom is True
    mock_session.commit.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_with_raw_bytes_and_none_key() -> None:
    # Arrange
    config_bytes = _make_config(
        user_id="usr_02",
        encrypted_api_key=b"raw_bytes_key",
    )
    mock_session = _make_async_session_mock(returned_model=None)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserAiConfigRepository(session_factory=mock_session_factory)

    # Act
    await repo.save(config_bytes)

    # Assert
    added_model = mock_session.add.call_args[0][0]
    assert added_model.encrypted_api_key == "raw_bytes_key"

    # Arrange 2: config without key
    config_none = _make_config(
        user_id="usr_03",
        provider=AIProvider.KOSMO_DEFAULT,
        model=DEFAULT_AI_MODEL,
        encrypted_api_key=None,
        is_custom=False,
    )
    # Act 2
    await repo.save(config_none)

    # Assert 2
    added_model_none = mock_session.add.call_args_list[1][0][0]
    assert added_model_none.encrypted_api_key is None
    assert added_model_none.is_custom is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_by_user_id_returns_entity_when_found() -> None:
    # Arrange
    now = datetime.now(UTC)
    existing_model = UserAiConfigModel(
        id="uai_01",
        user_id="usr_42",
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        encrypted_api_key="encrypted_key_abc",
        is_custom=True,
        created_at=now,
        updated_at=now,
    )
    mock_session = _make_async_session_mock(returned_model=existing_model)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserAiConfigRepository(session_factory=mock_session_factory)

    # Act
    result = await repo.by_user_id("usr_42")

    # Assert
    assert result is not None
    assert result.user_id == "usr_42"
    assert result.provider == AIProvider.ANTHROPIC
    assert result.model == "claude-3-5-sonnet-20241022"
    assert isinstance(result.encrypted_api_key, EncryptedSecret)
    assert result.encrypted_api_key.ciphertext == b"encrypted_key_abc"
    assert result.is_custom is True
    assert result.created_at == now
    assert result.updated_at == now


@pytest.mark.unit
@pytest.mark.asyncio
async def test_by_user_id_returns_none_when_not_found() -> None:
    # Arrange
    mock_session = _make_async_session_mock(returned_model=None)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserAiConfigRepository(session_factory=mock_session_factory)

    # Act
    result = await repo.by_user_id("usr_nonexistent")

    # Assert
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_by_user_id_handles_invalid_provider_gracefully_falling_back_to_default() -> None:
    # Arrange
    now = datetime.now(UTC)
    invalid_provider_model = UserAiConfigModel(
        id="uai_unknown",
        user_id="usr_unknown",
        provider="unsupported_provider_xyz",
        model="custom-model",
        encrypted_api_key=None,
        is_custom=False,
        created_at=now,
        updated_at=now,
    )
    mock_session = _make_async_session_mock(returned_model=invalid_provider_model)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserAiConfigRepository(session_factory=mock_session_factory)

    # Act
    result = await repo.by_user_id("usr_unknown")

    # Assert
    assert result is not None
    assert result.provider == DEFAULT_AI_PROVIDER
    assert result.encrypted_api_key is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_removes_user_ai_config() -> None:
    # Arrange
    mock_session = _make_async_session_mock(returned_model=None)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserAiConfigRepository(session_factory=mock_session_factory)

    # Act
    await repo.delete("usr_01")

    # Assert
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_repository_with_direct_session_does_not_commit() -> None:
    # Arrange
    mock_session = _make_async_session_mock(returned_model=None)
    repo = SqlAlchemyUserAiConfigRepository(session=mock_session)
    config = _make_config(user_id="usr_trans")

    # Act
    await repo.save(config)

    # Assert
    mock_session.add.assert_called_once()
    # When initialized with direct session, commit is delegated to the caller / UoW
    mock_session.commit.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_in_memory_user_ai_config_repository() -> None:
    # Arrange
    from tests.unit.fakes import InMemoryUserAiConfigRepository

    repo: UserAiConfigRepository = InMemoryUserAiConfigRepository()
    config = _make_config(user_id="usr_fake", provider=AIProvider.GOOGLE, model="gemini-2.5-flash")

    # Act - Save
    saved = await repo.save(config)

    # Assert - Save
    assert saved == config

    # Act - Retrieve
    fetched = await repo.by_user_id("usr_fake")

    # Assert - Retrieve
    assert fetched == config

    # Act - Not found
    not_found = await repo.by_user_id("usr_missing")

    # Assert - Not found
    assert not_found is None

    # Act - Delete
    await repo.delete("usr_fake")
    deleted_fetch = await repo.by_user_id("usr_fake")

    # Assert - Delete
    assert deleted_fetch is None
