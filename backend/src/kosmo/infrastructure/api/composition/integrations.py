from __future__ import annotations

from dataclasses import dataclass

from kosmo.application.integrations.execute_ephemeral_validation import (
    ExecuteEphemeralValidationUseCase,
)
from kosmo.application.integrations.link_github_account import LinkGitHubAccountUseCase
from kosmo.application.integrations.sync_github_repository import SyncGitHubRepositoryUseCase
from kosmo.config import Settings
from kosmo.contracts.auth import SecretCipher
from kosmo.contracts.integrations.git import GitWorkspacePort
from kosmo.contracts.integrations.github import GitHubClientPort
from kosmo.contracts.sdd.codegen import CodeRunnerPort, WorkspaceManagerPort
from kosmo.infrastructure.git import LocalGitWorkspaceAdapter
from kosmo.infrastructure.integrations.github_client import GitHubHttpClient
from kosmo.infrastructure.persistence.postgres.registry import RepositoryRegistry
from kosmo.infrastructure.sandbox.docker_runner import EphemeralDockerCodeRunner


@dataclass(frozen=True, slots=True)
class IntegrationsComponents:
    """Componentes cableados para integraciones con servicios externos (GitHub, OAuth)."""

    link_github_account: LinkGitHubAccountUseCase
    sync_github_repository: SyncGitHubRepositoryUseCase
    execute_ephemeral_validation: ExecuteEphemeralValidationUseCase
    github_client: GitHubClientPort
    git_workspace: GitWorkspacePort


def build_integrations_components(
    settings: Settings,
    repos: RepositoryRegistry,
    workspace_manager: WorkspaceManagerPort,
    cipher: SecretCipher,
    code_runner: CodeRunnerPort | None = None,
) -> IntegrationsComponents:
    github_client = GitHubHttpClient()
    git_workspace = LocalGitWorkspaceAdapter()
    runner = code_runner or EphemeralDockerCodeRunner()

    ephemeral_validator = ExecuteEphemeralValidationUseCase(
        code_runner=runner,
        workspace_manager=workspace_manager,
    )

    client_id = settings.github_client_id or ""
    client_secret = (
        settings.github_client_secret.get_secret_value() if settings.github_client_secret is not None else ""
    )

    link_github_account = LinkGitHubAccountUseCase(
        oauth_client=github_client,
        cipher=cipher,
        repo=repos.user_github_integrations,
        client_id=client_id,
        client_secret=client_secret,
    )

    sync_github_repository = SyncGitHubRepositoryUseCase(
        project_github_repo=repos.project_integrations,
        user_github_repo=repos.user_github_integrations,
        github_client=github_client,
        git_workspace=git_workspace,
        workspace_manager=workspace_manager,
        cipher=cipher,
        sync_log_repo=repos.sync_logs,
        ephemeral_validator=ephemeral_validator,
    )

    return IntegrationsComponents(
        link_github_account=link_github_account,
        sync_github_repository=sync_github_repository,
        execute_ephemeral_validation=ephemeral_validator,
        github_client=github_client,
        git_workspace=git_workspace,
    )
