from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.integrations.deployment import (
    DeploymentProvider,
    UserDeploymentIntegration,
)
from kosmo.contracts.integrations.github import UserGitHubIntegration
from kosmo.contracts.integrations.user_integration import (
    IntegrationProvider,
    UserIntegration,
)
from kosmo.contracts.sdd.ids import UserId
from kosmo.infrastructure.persistence.postgres.models import UserIntegrationModel
from kosmo.infrastructure.persistence.postgres.repositories.user_integration_repo import (
    SqlAlchemyUserDeploymentIntegrationRepository,
    SqlAlchemyUserGitHubIntegrationRepository,
    SqlAlchemyUserIntegrationRepository,
)


def _make_integration(
    user_id: str = "usr_01J00000000000000000000001",
    provider: IntegrationProvider = IntegrationProvider.GITHUB,
    encrypted_access_token: str = "gasp_encrypted_token_abc",
    account_name: str | None = "octocat",
    encrypted_refresh_token: str | None = None,
    scopes: list[str] | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> UserIntegration:
    now = datetime.now(UTC)
    return UserIntegration(
        user_id=UserId(user_id),
        provider=provider,
        encrypted_access_token=encrypted_access_token,
        account_name=account_name,
        encrypted_refresh_token=encrypted_refresh_token,
        scopes=scopes or ["repo", "user"],
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


def _make_async_session_mock(
    returned_model: UserIntegrationModel | None = None,
    returned_models: list[UserIntegrationModel] | None = None,
    rowcount: int = 1,
) -> MagicMock:
    mock_session = MagicMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = returned_model
    mock_scalars = MagicMock()
    if returned_models is not None:
        mock_scalars.all.return_value = returned_models
    else:
        mock_scalars.all.return_value = [returned_model] if returned_model else []
    mock_result.scalars.return_value = mock_scalars
    mock_result.rowcount = rowcount

    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()
    return mock_session


@pytest.mark.unit
@pytest.mark.asyncio
async def test_init_raises_without_session_or_factory() -> None:
    # Arrange & Act & Assert
    with pytest.raises(ValueError, match="Se requiere session_factory o session"):
        SqlAlchemyUserIntegrationRepository(session_factory=None, session=None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_inserts_new_user_integration_when_none_exists() -> None:
    # Arrange
    integration = _make_integration(
        user_id="usr_01J00000000000000000000001",
        provider=IntegrationProvider.GITHUB,
        account_name="octocat",
        encrypted_access_token="enc_token_123",
        scopes=["repo", "workflow"],
    )
    mock_session = _make_async_session_mock(returned_model=None)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserIntegrationRepository(session_factory=mock_session_factory)

    # Act
    result = await repo.save(integration)

    # Assert
    assert result == integration
    mock_session.add.assert_called_once()
    added_model: UserIntegrationModel = mock_session.add.call_args[0][0]
    assert added_model.user_id == "usr_01J00000000000000000000001"
    assert added_model.provider == "github"
    assert added_model.account_name == "octocat"
    assert added_model.access_token_enc == "enc_token_123"
    assert added_model.scopes == ["repo", "workflow"]
    mock_session.commit.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_updates_existing_user_integration() -> None:
    # Arrange
    now = datetime.now(UTC)
    updated_integration = _make_integration(
        user_id="usr_01J00000000000000000000001",
        provider=IntegrationProvider.GITHUB,
        account_name="octocat_new",
        encrypted_access_token="new_enc_token",
        scopes=["repo"],
    )
    existing_model = UserIntegrationModel(
        id="uint_01",
        user_id="usr_01J00000000000000000000001",
        provider="github",
        account_name="octocat_old",
        access_token_enc="old_enc_token",
        refresh_token_enc=None,
        scopes=["repo", "user"],
        created_at=now,
        updated_at=now,
    )
    mock_session = _make_async_session_mock(returned_model=existing_model)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserIntegrationRepository(session_factory=mock_session_factory)

    # Act
    result = await repo.save(updated_integration)

    # Assert
    assert result == updated_integration
    assert existing_model.account_name == "octocat_new"
    assert existing_model.access_token_enc == "new_enc_token"
    assert existing_model.scopes == ["repo"]
    mock_session.commit.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_by_user_and_provider_returns_entity_when_found() -> None:
    # Arrange
    now = datetime.now(UTC)
    existing_model = UserIntegrationModel(
        id="uint_01",
        user_id="usr_01J00000000000000000000042",
        provider="railway",
        account_name="railway-user",
        access_token_enc="enc_railway_secret",
        refresh_token_enc="enc_railway_refresh",
        scopes=["project:read", "project:write"],
        created_at=now,
        updated_at=now,
    )
    mock_session = _make_async_session_mock(returned_model=existing_model)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserIntegrationRepository(session_factory=mock_session_factory)

    # Act
    result = await repo.get_by_user_and_provider(
        user_id=UserId("usr_01J00000000000000000000042"),
        provider=IntegrationProvider.RAILWAY,
    )

    # Assert
    assert result is not None
    assert result.user_id == UserId("usr_01J00000000000000000000042")
    assert result.provider == IntegrationProvider.RAILWAY
    assert result.account_name == "railway-user"
    assert result.encrypted_access_token == "enc_railway_secret"
    assert result.encrypted_refresh_token == "enc_railway_refresh"
    assert result.scopes == ["project:read", "project:write"]
    assert result.created_at == now
    assert result.updated_at == now


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_by_user_and_provider_returns_none_when_not_found() -> None:
    # Arrange
    mock_session = _make_async_session_mock(returned_model=None)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserIntegrationRepository(session_factory=mock_session_factory)

    # Act
    result = await repo.get_by_user_and_provider(
        user_id=UserId("usr_01J00000000000000000000000"),
        provider=IntegrationProvider.GITHUB,
    )

    # Assert
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_removes_user_integration_and_returns_true() -> None:
    # Arrange
    mock_session = _make_async_session_mock(rowcount=1)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserIntegrationRepository(session_factory=mock_session_factory)

    # Act
    deleted = await repo.delete(
        user_id=UserId("usr_01J00000000000000000000001"),
        provider=IntegrationProvider.GITHUB,
    )

    # Assert
    assert deleted is True
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_returns_false_when_nothing_deleted() -> None:
    # Arrange
    mock_session = _make_async_session_mock(rowcount=0)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserIntegrationRepository(session_factory=mock_session_factory)

    # Act
    deleted = await repo.delete(
        user_id=UserId("usr_nonexistent"),
        provider=IntegrationProvider.GITHUB,
    )

    # Assert
    assert deleted is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_by_user_returns_all_integrations_for_user() -> None:
    # Arrange
    now = datetime.now(UTC)
    model1 = UserIntegrationModel(
        id="uint_01",
        user_id="usr_01J00000000000000000000001",
        provider="github",
        account_name="octocat",
        access_token_enc="enc_gh",
        refresh_token_enc=None,
        scopes=["repo"],
        created_at=now,
        updated_at=now,
    )
    model2 = UserIntegrationModel(
        id="uint_02",
        user_id="usr_01J00000000000000000000001",
        provider="railway",
        account_name="octo-railway",
        access_token_enc="enc_rw",
        refresh_token_enc=None,
        scopes=["deploy"],
        created_at=now,
        updated_at=now,
    )
    mock_session = _make_async_session_mock(returned_models=[model1, model2])
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserIntegrationRepository(session_factory=mock_session_factory)

    # Act
    integrations = await repo.list_by_user(UserId("usr_01J00000000000000000000001"))

    # Assert
    assert len(integrations) == 2
    assert integrations[0].provider == IntegrationProvider.GITHUB
    assert integrations[1].provider == IntegrationProvider.RAILWAY


@pytest.mark.unit
@pytest.mark.asyncio
async def test_repository_with_direct_session_delegates_commit() -> None:
    # Arrange
    mock_session = _make_async_session_mock(returned_model=None)
    repo = SqlAlchemyUserIntegrationRepository(session=mock_session)
    integration = _make_integration(user_id="usr_trans")

    # Act
    await repo.save(integration)

    # Assert
    mock_session.add.assert_called_once()
    mock_session.commit.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_github_integration_repository_adapter() -> None:
    # Arrange
    now = datetime.now(UTC)
    gh_model = UserIntegrationModel(
        id="uint_gh_01",
        user_id="usr_01J00000000000000000000099",
        provider="github",
        account_name="octocat_dev",
        access_token_enc="encrypted_gho_token",
        refresh_token_enc=None,
        scopes=["repo"],
        created_at=now,
        updated_at=now,
    )
    mock_session = _make_async_session_mock(returned_model=gh_model)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserGitHubIntegrationRepository(session_factory=mock_session_factory)

    # Act - Get
    fetched = await repo.get_by_user_id(UserId("usr_01J00000000000000000000099"))

    # Assert - Get
    assert fetched is not None
    assert fetched.user_id == UserId("usr_01J00000000000000000000099")
    assert fetched.github_username == "octocat_dev"
    assert fetched.encrypted_token == "encrypted_gho_token"

    # Act - Save
    new_integration = UserGitHubIntegration(
        user_id=UserId("usr_01J00000000000000000000099"),
        github_username="octocat_updated",
        encrypted_token="new_encrypted_gho_token",
    )
    await repo.save(new_integration)

    # Assert - Save
    mock_session.commit.assert_awaited()

    # Act - Delete
    deleted = await repo.delete_by_user_id(UserId("usr_01J00000000000000000000099"))
    assert deleted is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_in_memory_user_integration_repository() -> None:
    # Arrange
    from tests.unit.fakes import (
        InMemoryUserGitHubIntegrationRepository,
        InMemoryUserIntegrationRepository,
    )

    repo = InMemoryUserIntegrationRepository()
    user_a = UserId("usr_A")
    user_b = UserId("usr_B")

    int_a_gh = _make_integration(user_id=str(user_a), provider=IntegrationProvider.GITHUB)
    int_a_rw = _make_integration(user_id=str(user_a), provider=IntegrationProvider.RAILWAY)
    int_b_gh = _make_integration(user_id=str(user_b), provider=IntegrationProvider.GITHUB)

    # Act - Save
    await repo.save(int_a_gh)
    await repo.save(int_a_rw)
    await repo.save(int_b_gh)

    # Assert - Isolation
    list_a = await repo.list_by_user(user_a)
    assert len(list_a) == 2

    list_b = await repo.list_by_user(user_b)
    assert len(list_b) == 1
    assert list_b[0].user_id == user_b

    # Act - Delete
    deleted = await repo.delete(user_a, IntegrationProvider.GITHUB)
    assert deleted is True

    # Assert - Delete
    fetched_deleted = await repo.get_by_user_and_provider(user_a, IntegrationProvider.GITHUB)
    assert fetched_deleted is None

    # User B's GitHub integration still exists
    fetched_b = await repo.get_by_user_and_provider(user_b, IntegrationProvider.GITHUB)
    assert fetched_b is not None

    # InMemory GitHub adapter
    gh_repo = InMemoryUserGitHubIntegrationRepository()
    gh_int = UserGitHubIntegration(
        user_id=user_a,
        github_username="octo",
        encrypted_token="enc_token",
    )
    await gh_repo.save(gh_int)
    assert await gh_repo.get_by_user_id(user_a) == gh_int
    assert await gh_repo.delete_by_user_id(user_a) is True
    assert await gh_repo.get_by_user_id(user_a) is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_deployment_integration_repository_adapter() -> None:
    # Arrange
    now = datetime.now(UTC)
    rw_model = UserIntegrationModel(
        id="uint_rw_01",
        user_id="usr_01J00000000000000000000099",
        provider="railway",
        account_name="railway_dev",
        access_token_enc="encrypted_rw_token",
        refresh_token_enc="encrypted_rw_refresh",
        scopes=["openid", "workspace:admin"],
        created_at=now,
        updated_at=now,
    )
    mock_session = _make_async_session_mock(returned_model=rw_model)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyUserDeploymentIntegrationRepository(session_factory=mock_session_factory)

    # Act - Get
    fetched = await repo.get_by_user_id(UserId("usr_01J00000000000000000000099"))

    # Assert - Get
    assert fetched is not None
    assert fetched.user_id == UserId("usr_01J00000000000000000000099")
    assert fetched.provider == DeploymentProvider.RAILWAY
    assert fetched.provider_username == "railway_dev"
    assert fetched.encrypted_token == "encrypted_rw_token"
    assert fetched.encrypted_refresh_token == "encrypted_rw_refresh"
    assert fetched.scopes == ("openid", "workspace:admin")

    # Act - Save
    new_integration = UserDeploymentIntegration(
        user_id=UserId("usr_01J00000000000000000000099"),
        provider=DeploymentProvider.RAILWAY,
        provider_username="railway_updated",
        encrypted_token="new_encrypted_rw_token",
        encrypted_refresh_token="new_encrypted_refresh",
        scopes=("workspace:admin",),
    )
    await repo.save(new_integration)

    # Assert - Save
    mock_session.commit.assert_awaited()

    # Act - Delete
    deleted = await repo.delete_by_user_id(UserId("usr_01J00000000000000000000099"))
    assert deleted is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_in_memory_user_deployment_integration_repository() -> None:
    # Arrange
    from tests.unit.fakes import InMemoryUserDeploymentIntegrationRepository

    repo = InMemoryUserDeploymentIntegrationRepository()
    user_id = UserId("usr_DEPLOY_TEST")

    int_rw = UserDeploymentIntegration(
        user_id=user_id,
        provider=DeploymentProvider.RAILWAY,
        provider_username="rw_user",
        encrypted_token="enc_rw_token",
    )

    # Act - Save
    await repo.save(int_rw)

    # Assert - Get
    assert await repo.get_by_user_id(user_id) == int_rw

    # Act - Delete
    assert await repo.delete_by_user_id(user_id) is True
    assert await repo.get_by_user_id(user_id) is None
    assert await repo.delete_by_user_id(user_id) is False
