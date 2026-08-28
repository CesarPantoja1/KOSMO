"""Contratos de integraciÃ³n con servicios externos."""

from kosmo.contracts.integrations.git import GitWorkspacePort
from kosmo.contracts.integrations.github import (
    CodeSyncLog,
    CodeSyncStatus,
    GitHubApiError,
    GitHubAuthenticationError,
    GitHubClientPort,
    GitHubOAuthToken,
    GitHubPermissionError,
    GitHubRateLimitError,
    GitHubRepository,
    GitHubRepositoryAlreadyExistsError,
    GitHubResourceNotFoundError,
    GitHubSyncStatus,
    GitHubUser,
    ProjectGitHubIntegration,
    ProjectGitHubIntegrationRepository,
    UserGitHubIntegration,
    UserGitHubIntegrationRepository,
)
from kosmo.contracts.integrations.user_integration import (
    IntegrationProvider,
    UserIntegration,
    UserIntegrationRepository,
)

__all__ = [
    "GitWorkspacePort",
    "CodeSyncLog",
    "CodeSyncStatus",
    "GitHubApiError",
    "GitHubAuthenticationError",
    "GitHubClientPort",
    "GitHubOAuthToken",
    "GitHubPermissionError",
    "GitHubRateLimitError",
    "GitHubRepository",
    "GitHubRepositoryAlreadyExistsError",
    "GitHubResourceNotFoundError",
    "GitHubSyncStatus",
    "GitHubUser",
    "IntegrationProvider",
    "ProjectGitHubIntegration",
    "ProjectGitHubIntegrationRepository",
    "UserGitHubIntegration",
    "UserGitHubIntegrationRepository",
    "UserIntegration",
    "UserIntegrationRepository",
]
