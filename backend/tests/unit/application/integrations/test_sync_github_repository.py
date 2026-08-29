from __future__ import annotations

import base64
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from kosmo.application.integrations.execute_ephemeral_validation import (
    EphemeralValidationError,
    ExecuteEphemeralValidationResult,
)
from kosmo.application.integrations.sync_github_repository import (
    SyncGitHubRepositoryCommand,
    SyncGitHubRepositoryUseCase,
)
from kosmo.contracts.integrations.git import GitWorkspacePort
from kosmo.contracts.integrations.github import (
    CodeSyncStatus,
    GitHubRepository,
    GitHubSyncStatus,
    GitHubUser,
    ProjectGitHubIntegration,
    UserGitHubIntegration,
)
from kosmo.contracts.sdd.codegen import CodeWorkspace, ValidationStep
from kosmo.contracts.sdd.ids import ProjectId, UserId, WorkspaceId
from kosmo.infrastructure.git import GitError


@pytest.fixture
def project_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def user_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def github_client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def git_workspace() -> MagicMock:
    return MagicMock(spec=GitWorkspacePort)


@pytest.fixture
def workspace_manager() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def cipher() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sync_log_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def use_case(
    project_repo: AsyncMock,
    user_repo: AsyncMock,
    github_client: AsyncMock,
    git_workspace: MagicMock,
    workspace_manager: AsyncMock,
    cipher: MagicMock,
    sync_log_repo: AsyncMock,
) -> SyncGitHubRepositoryUseCase:
    return SyncGitHubRepositoryUseCase(
        project_github_repo=project_repo,
        user_github_repo=user_repo,
        github_client=github_client,
        git_workspace=git_workspace,
        workspace_manager=workspace_manager,
        cipher=cipher,
        sync_log_repo=sync_log_repo,
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_sync_github_repository_incremental_push_success(
    use_case: SyncGitHubRepositoryUseCase,
    project_repo: AsyncMock,
    user_repo: AsyncMock,
    github_client: AsyncMock,
    git_workspace: MagicMock,
    workspace_manager: AsyncMock,
    cipher: MagicMock,
    sync_log_repo: AsyncMock,
) -> None:
    # Arrange
    project_id = ProjectId("proj-existing")
    user_id = UserId("usr-octo")
    previous_push = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)

    existing_integration = ProjectGitHubIntegration(
        project_id=project_id,
        repo_name="kosmo-crm-app",
        repo_url="https://github.com/octocat/kosmo-crm-app.git",
        is_public=False,
        default_branch="main",
        last_push_at=previous_push,
        last_commit_hash="commit_hash_v1",
        sync_status=GitHubSyncStatus.SYNCED,
    )
    project_repo.get_by_project_id.return_value = existing_integration
    project_repo.save.side_effect = lambda integration: integration

    user_repo.get_by_user_id.return_value = UserGitHubIntegration(
        user_id=user_id,
        github_username="octocat",
        encrypted_token=base64.b64encode(b"encrypted_secret_token").decode("utf-8"),
    )
    cipher.decrypt.return_value = b"ghp_real_decrypted_token"

    workspace_manager.get_workspace.return_value = CodeWorkspace(
        id=WorkspaceId("ws-proj-1"),
        project_id=project_id,
        workspace_dir="/tmp/workspaces/proj-existing",
    )

    git_workspace.build_authenticated_url.return_value = (
        "https://x-access-token:ghp_real_decrypted_token@github.com/octocat/kosmo-crm-app.git"
    )
    git_workspace.push.return_value = "new_commit_hash_v2"

    cmd = SyncGitHubRepositoryCommand(project_id=project_id)

    # Act
    result = await use_case.execute(cmd, user_id)

    # Assert
    # 1. No debe llamar a create_repository ni check_repository_exists porque es push incremental
    github_client.create_repository.assert_not_called()
    github_client.check_repository_exists.assert_not_called()

    # 2. Debe configurar remote con token fresco y pushear
    git_workspace.remote_add_or_update.assert_called_once_with(
        "/tmp/workspaces/proj-existing",
        "origin",
        "https://x-access-token:ghp_real_decrypted_token@github.com/octocat/kosmo-crm-app.git",
    )
    git_workspace.push.assert_called_once_with(
        "/tmp/workspaces/proj-existing",
        "origin",
        branch="main",
    )

    # 3. Metadatos y timestamps actualizados
    assert result.sync_status == GitHubSyncStatus.SYNCED
    assert result.last_commit_hash == "new_commit_hash_v2"
    assert result.last_push_at is not None
    assert result.last_push_at > previous_push
    assert result.last_synced_at == result.last_push_at
    assert result.error_message is None

    # 4. Auditoría registrada
    sync_log_repo.add_log.assert_called_once()
    logged_entry = sync_log_repo.add_log.call_args[0][0]
    assert logged_entry.status == CodeSyncStatus.SUCCESS
    assert logged_entry.commit_sha == "new_commit_hash_v2"
    assert "https://github.com/octocat/kosmo-crm-app.git" in logged_entry.message


@pytest.mark.asyncio
@pytest.mark.unit
async def test_sync_github_repository_incremental_push_recovers_from_previous_failure(
    use_case: SyncGitHubRepositoryUseCase,
    project_repo: AsyncMock,
    user_repo: AsyncMock,
    git_workspace: MagicMock,
    workspace_manager: AsyncMock,
    cipher: MagicMock,
) -> None:
    # Arrange
    project_id = ProjectId("proj-failed-before")
    user_id = UserId("usr-octo")

    failed_integration = ProjectGitHubIntegration(
        project_id=project_id,
        repo_name="kosmo-crm-app",
        repo_url="https://github.com/octocat/kosmo-crm-app.git",
        sync_status=GitHubSyncStatus.FAILED,
        error_message="Connection timeout on previous attempt",
    )
    project_repo.get_by_project_id.return_value = failed_integration
    project_repo.save.side_effect = lambda integration: integration

    user_repo.get_by_user_id.return_value = UserGitHubIntegration(
        user_id=user_id,
        github_username="octocat",
        encrypted_token=base64.b64encode(b"encrypted").decode("utf-8"),
    )
    cipher.decrypt.return_value = b"token"
    workspace_manager.get_workspace.return_value = CodeWorkspace(
        id=WorkspaceId("ws-1"), project_id=project_id, workspace_dir="/tmp/ws"
    )
    git_workspace.build_authenticated_url.return_value = "https://auth-url"
    git_workspace.push.return_value = "recovered_hash_123"

    cmd = SyncGitHubRepositoryCommand(project_id=project_id)

    # Act
    result = await use_case.execute(cmd, user_id)

    # Assert
    assert result.sync_status == GitHubSyncStatus.SYNCED
    assert result.error_message is None
    assert result.last_commit_hash == "recovered_hash_123"
    assert result.last_push_at is not None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_sync_github_repository_incremental_push_fails_when_git_push_fails(
    use_case: SyncGitHubRepositoryUseCase,
    project_repo: AsyncMock,
    user_repo: AsyncMock,
    git_workspace: MagicMock,
    workspace_manager: AsyncMock,
    cipher: MagicMock,
    sync_log_repo: AsyncMock,
) -> None:
    # Arrange
    project_id = ProjectId("proj-1")
    user_id = UserId("usr-1")

    existing_integration = ProjectGitHubIntegration(
        project_id=project_id,
        repo_name="proj-1-repo",
        repo_url="https://github.com/octocat/proj-1-repo.git",
        sync_status=GitHubSyncStatus.SYNCED,
    )
    project_repo.get_by_project_id.return_value = existing_integration
    project_repo.save.side_effect = lambda integration: integration

    user_repo.get_by_user_id.return_value = UserGitHubIntegration(
        user_id=user_id,
        github_username="octocat",
        encrypted_token=base64.b64encode(b"enc").decode("utf-8"),
    )
    cipher.decrypt.return_value = b"token"
    workspace_manager.get_workspace.return_value = CodeWorkspace(
        id=WorkspaceId("ws-1"), project_id=project_id, workspace_dir="/tmp/ws-1"
    )
    git_workspace.build_authenticated_url.return_value = "https://auth-url"
    git_workspace.push.side_effect = GitError("Fallo al ejecutar git push: rejected non-fast-forward")

    cmd = SyncGitHubRepositoryCommand(project_id=project_id)

    # Act & Assert
    with pytest.raises(GitError, match="rejected non-fast-forward"):
        await use_case.execute(cmd, user_id)

    # Verificar que el estado se actualizó a FAILED con el mensaje de error
    saved_states = [call[0][0] for call in project_repo.save.call_args_list]
    final_saved_state = saved_states[-1]
    assert final_saved_state.sync_status == GitHubSyncStatus.FAILED
    assert "rejected non-fast-forward" in (final_saved_state.error_message or "")

    # Verificar log de fallo
    sync_log_repo.add_log.assert_called_once()
    saved_log = sync_log_repo.add_log.call_args[0][0]
    assert saved_log.status == CodeSyncStatus.FAILED
    assert "rejected non-fast-forward" in (saved_log.message or "")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_sync_github_repository_raises_when_user_not_linked(
    use_case: SyncGitHubRepositoryUseCase,
    user_repo: AsyncMock,
) -> None:
    # Arrange
    user_repo.get_by_user_id.return_value = None
    cmd = SyncGitHubRepositoryCommand(project_id=ProjectId("proj-1"))

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        await use_case.execute(cmd, UserId("usr-unlinked"))

    assert "vinculada con GitHub" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_sync_github_repository_raises_when_workspace_not_found(
    use_case: SyncGitHubRepositoryUseCase,
    user_repo: AsyncMock,
    workspace_manager: AsyncMock,
) -> None:
    # Arrange
    user_repo.get_by_user_id.return_value = UserGitHubIntegration(
        user_id=UserId("usr-1"),
        github_username="octocat",
        encrypted_token=base64.b64encode(b"enc").decode("utf-8"),
    )
    workspace_manager.get_workspace.return_value = None
    cmd = SyncGitHubRepositoryCommand(project_id=ProjectId("proj-1"))

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        await use_case.execute(cmd, UserId("usr-1"))

    assert "directorio físico del workspace" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_sync_github_repository_first_push_creates_repo_and_sets_metadata(
    use_case: SyncGitHubRepositoryUseCase,
    project_repo: AsyncMock,
    user_repo: AsyncMock,
    github_client: AsyncMock,
    git_workspace: MagicMock,
    workspace_manager: AsyncMock,
    cipher: MagicMock,
    sync_log_repo: AsyncMock,
) -> None:
    # Arrange
    project_id = ProjectId("proj-initial")
    user_id = UserId("usr-1")

    project_repo.get_by_project_id.return_value = None
    project_repo.save.side_effect = lambda integration: integration

    user_repo.get_by_user_id.return_value = UserGitHubIntegration(
        user_id=user_id,
        github_username="octocat",
        encrypted_token=base64.b64encode(b"enc").decode("utf-8"),
    )
    cipher.decrypt.return_value = b"token"
    workspace_manager.get_workspace.return_value = CodeWorkspace(
        id=WorkspaceId("ws-1"), project_id=project_id, workspace_dir="/tmp/ws-initial"
    )

    github_client.get_authenticated_user.return_value = GitHubUser(login="octocat", id=1)
    github_client.check_repository_exists.return_value = False
    github_client.create_repository.return_value = GitHubRepository(
        id=456,
        name="custom-repo-name",
        full_name="octocat/custom-repo-name",
        clone_url="https://github.com/octocat/custom-repo-name.git",
        html_url="https://github.com/octocat/custom-repo-name",
        owner="octocat",
        is_private=True,
    )
    git_workspace.build_authenticated_url.return_value = "https://auth-url"
    git_workspace.push.return_value = "initial_hash_001"

    cmd = SyncGitHubRepositoryCommand(
        project_id=project_id,
        repo_name="custom-repo-name",
        is_public=False,
        commit_message="feat: initial project generation",
    )

    # Act
    result = await use_case.execute(cmd, user_id)

    # Assert
    github_client.create_repository.assert_called_once_with(
        token="token",
        name="custom-repo-name",
        description="Repositorio sincronizado automáticamente desde KOSMO para proyecto proj-initial",
        is_private=True,
    )
    git_workspace.remote_add_or_update.assert_called_once_with("/tmp/ws-initial", "origin", "https://auth-url")
    git_workspace.push.assert_called_once_with("/tmp/ws-initial", "origin", branch="main")

    assert result.sync_status == GitHubSyncStatus.SYNCED
    assert result.repo_url == "https://github.com/octocat/custom-repo-name.git"
    assert result.repo_name == "custom-repo-name"
    assert result.last_commit_hash == "initial_hash_001"
    assert result.last_push_at is not None
    assert result.last_synced_at is not None

    sync_log_repo.add_log.assert_called_once()
    logged_entry = sync_log_repo.add_log.call_args[0][0]
    assert logged_entry.status == CodeSyncStatus.SUCCESS
    assert logged_entry.commit_sha == "initial_hash_001"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_sync_github_repository_fails_when_ephemeral_validation_fails(
    project_repo: AsyncMock,
    user_repo: AsyncMock,
    github_client: AsyncMock,
    git_workspace: MagicMock,
    workspace_manager: AsyncMock,
    cipher: MagicMock,
    sync_log_repo: AsyncMock,
) -> None:
    # Arrange
    project_id = ProjectId("proj-ephem-fail")
    user_id = UserId("usr-1")

    existing_integration = ProjectGitHubIntegration(
        project_id=project_id,
        repo_name="proj-repo",
        repo_url="https://github.com/octocat/proj-repo.git",
        sync_status=GitHubSyncStatus.SYNCED,
    )
    project_repo.get_by_project_id.return_value = existing_integration
    project_repo.save.side_effect = lambda integration: integration

    user_repo.get_by_user_id.return_value = UserGitHubIntegration(
        user_id=user_id,
        github_username="octocat",
        encrypted_token=base64.b64encode(b"enc").decode("utf-8"),
    )
    cipher.decrypt.return_value = b"token"
    workspace_manager.get_workspace.return_value = CodeWorkspace(
        id=WorkspaceId("ws-1"), project_id=project_id, workspace_dir="/tmp/ws-1"
    )

    ephemeral_validator = AsyncMock()
    ephemeral_validator.execute.return_value = ExecuteEphemeralValidationResult(
        is_valid=False,
        failed_step=ValidationStep.TESTS,
        error_summary=("Vitest failed with 2 failing tests",),
        steps=(),
    )

    use_case = SyncGitHubRepositoryUseCase(
        project_github_repo=project_repo,
        user_github_repo=user_repo,
        github_client=github_client,
        git_workspace=git_workspace,
        workspace_manager=workspace_manager,
        cipher=cipher,
        sync_log_repo=sync_log_repo,
        ephemeral_validator=ephemeral_validator,
    )

    cmd = SyncGitHubRepositoryCommand(project_id=project_id)

    # Act & Assert
    with pytest.raises(EphemeralValidationError) as exc_info:
        await use_case.execute(cmd, user_id)

    assert "Validación efímera fallida en el paso 'tests'" in str(exc_info.value)
    # Git push no debió ejecutarse
    git_workspace.push.assert_not_called()

    # Estado actualizado a FAILED
    saved_states = [call[0][0] for call in project_repo.save.call_args_list]
    final_saved_state = saved_states[-1]
    assert final_saved_state.sync_status == GitHubSyncStatus.FAILED
    assert "Validación efímera fallida" in (final_saved_state.error_message or "")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_sync_github_repository_proceeds_when_ephemeral_validation_passes(
    project_repo: AsyncMock,
    user_repo: AsyncMock,
    github_client: AsyncMock,
    git_workspace: MagicMock,
    workspace_manager: AsyncMock,
    cipher: MagicMock,
    sync_log_repo: AsyncMock,
) -> None:
    # Arrange
    project_id = ProjectId("proj-ephem-pass")
    user_id = UserId("usr-1")

    existing_integration = ProjectGitHubIntegration(
        project_id=project_id,
        repo_name="proj-repo",
        repo_url="https://github.com/octocat/proj-repo.git",
        sync_status=GitHubSyncStatus.SYNCED,
    )
    project_repo.get_by_project_id.return_value = existing_integration
    project_repo.save.side_effect = lambda integration: integration

    user_repo.get_by_user_id.return_value = UserGitHubIntegration(
        user_id=user_id,
        github_username="octocat",
        encrypted_token=base64.b64encode(b"enc").decode("utf-8"),
    )
    cipher.decrypt.return_value = b"token"
    workspace_manager.get_workspace.return_value = CodeWorkspace(
        id=WorkspaceId("ws-1"), project_id=project_id, workspace_dir="/tmp/ws-1"
    )
    git_workspace.build_authenticated_url.return_value = "https://auth-url"
    git_workspace.push.return_value = "valid_commit_hash_789"

    ephemeral_validator = AsyncMock()
    ephemeral_validator.execute.return_value = ExecuteEphemeralValidationResult(
        is_valid=True,
        steps=(),
        error_summary=(),
    )

    use_case = SyncGitHubRepositoryUseCase(
        project_github_repo=project_repo,
        user_github_repo=user_repo,
        github_client=github_client,
        git_workspace=git_workspace,
        workspace_manager=workspace_manager,
        cipher=cipher,
        sync_log_repo=sync_log_repo,
        ephemeral_validator=ephemeral_validator,
    )

    cmd = SyncGitHubRepositoryCommand(project_id=project_id)

    # Act
    result = await use_case.execute(cmd, user_id)

    # Assert
    ephemeral_validator.execute.assert_called_once()
    git_workspace.push.assert_called_once()
    assert result.sync_status == GitHubSyncStatus.SYNCED
    assert result.last_commit_hash == "valid_commit_hash_789"
