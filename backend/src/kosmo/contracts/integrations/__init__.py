"""Contratos de integración con servicios externos."""

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
    "GitHubUser",
    "IntegrationProvider",
    "ProjectGitHubIntegration",
    "ProjectGitHubIntegrationRepository",
    "UserGitHubIntegration",
    "UserGitHubIntegrationRepository",
    "UserIntegration",
    "UserIntegrationRepository",
]
