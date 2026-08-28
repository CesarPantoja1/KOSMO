import base64
from unittest.mock import AsyncMock, MagicMock

import pytest

from kosmo.application.integrations.sync_github_repository import (
    SyncGitHubRepositoryCommand,
    SyncGitHubRepositoryUseCase,
)
from kosmo.contracts.integrations.github import (
    CodeSyncStatus,
    GitHubRepository,
    GitHubUser,
    ProjectGitHubIntegration,
    UserGitHubIntegration,
)
from kosmo.contracts.sdd.codegen import CodeWorkspace
from kosmo.contracts.sdd.ids import ProjectId, UserId, WorkspaceId


@pytest.fixture
def project_repo():
    return AsyncMock()


@pytest.fixture
def user_repo():
    return AsyncMock()


@pytest.fixture
def github_client():
    return AsyncMock()


@pytest.fixture
def git_workspace():
    return MagicMock()


@pytest.fixture
def workspace_manager():
    return AsyncMock()


@pytest.fixture
def cipher():
    return MagicMock()


@pytest.fixture
def sync_log_repo():
    return AsyncMock()


@pytest.fixture
def use_case(
    project_repo,
    user_repo,
    github_client,
    git_workspace,
    workspace_manager,
    cipher,
    sync_log_repo,
):
    return SyncGitHubRepositoryUseCase(
        project_github_repo=project_repo,
        user_github_repo=user_repo,
        github_client=github_client,
        git_workspace=git_workspace,
        workspace_manager=workspace_manager,
        cipher=cipher,
        sync_log_repo=sync_log_repo,
    )


async def test_sync_github_repository_success_new_repo(
    use_case: SyncGitHubRepositoryUseCase,
    project_repo: AsyncMock,
    user_repo: AsyncMock,
    github_client: AsyncMock,
    git_workspace: MagicMock,
    workspace_manager: AsyncMock,
    cipher: MagicMock,
):
    cmd = SyncGitHubRepositoryCommand(project_id=ProjectId("proj-1"))

    project_repo.get_by_project_id.return_value = ProjectGitHubIntegration(
        project_id=ProjectId("proj-1"), repo_name="proj-1-repo"
    )
    user_repo.get_by_user_id.return_value = UserGitHubIntegration(
        user_id=UserId("user-1"), github_username="octocat", encrypted_token=base64.b64encode(b"enc").decode("utf-8")
    )
    workspace_manager.get_workspace.return_value = CodeWorkspace(
        id=WorkspaceId("ws-1"), project_id=ProjectId("proj-1"), workspace_dir="/tmp/ws-1"
    )

    cipher.decrypt.return_value = b"real-token"
    github_client.get_authenticated_user.return_value = GitHubUser(login="octocat", id=1)
    github_client.check_repository_exists.return_value = False
    github_client.create_repository.return_value = GitHubRepository(
        id=123,
        name="proj-1-repo",
        full_name="octocat/proj-1-repo",
        clone_url="https://github.com/octocat/proj-1-repo.git",
        html_url="https://github.com/octocat/proj-1-repo",
        owner="octocat",
        is_private=True,
    )

    git_workspace.build_authenticated_url.return_value = (
        "https://x-access-token:real-token@github.com/octocat/proj-1-repo.git"
    )
    git_workspace.push.return_value = "abc123hash"

    await use_case.execute(cmd, UserId("user-1"))

    # Assertions
    github_client.create_repository.assert_called_once()
    git_workspace.remote_add_or_update.assert_called_once_with(
        "/tmp/ws-1", "origin", "https://x-access-token:real-token@github.com/octocat/proj-1-repo.git"
    )
    git_workspace.push.assert_called_once_with("/tmp/ws-1", "origin")


async def test_sync_github_repository_fails_and_logs(
    use_case: SyncGitHubRepositoryUseCase,
    project_repo: AsyncMock,
    user_repo: AsyncMock,
    github_client: AsyncMock,
    workspace_manager: AsyncMock,
    sync_log_repo: AsyncMock,
    cipher: MagicMock,
):
    cmd = SyncGitHubRepositoryCommand(project_id=ProjectId("proj-1"))

    project_repo.get_by_project_id.return_value = ProjectGitHubIntegration(
        project_id=ProjectId("proj-1"), repo_name="proj-1-repo"
    )
    user_repo.get_by_user_id.return_value = UserGitHubIntegration(
        user_id=UserId("user-1"), github_username="octocat", encrypted_token=base64.b64encode(b"enc").decode("utf-8")
    )
    workspace_manager.get_workspace.return_value = CodeWorkspace(
        id=WorkspaceId("ws-1"), project_id=ProjectId("proj-1"), workspace_dir="/tmp/ws-1"
    )
    cipher.decrypt.return_value = b"real-token"

    # Simular error en la API de GitHub
    github_client.get_authenticated_user.side_effect = RuntimeError("API down")

    with pytest.raises(RuntimeError):
        await use_case.execute(cmd, UserId("user-1"))

    # Verificar log
    sync_log_repo.add_log.assert_called_once()
    saved_log = sync_log_repo.add_log.call_args[0][0]
    assert saved_log.status == CodeSyncStatus.FAILED
    assert "API down" in saved_log.message
