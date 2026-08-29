from __future__ import annotations

from fastapi import Request

from kosmo.application.integrations.execute_ephemeral_validation import (
    ExecuteEphemeralValidationUseCase,
)
from kosmo.application.integrations.link_github_account import LinkGitHubAccountUseCase
from kosmo.application.integrations.sync_github_repository import SyncGitHubRepositoryUseCase
from kosmo.infrastructure.api.dependencies.container import get_container


def get_link_github_account_use_case(request: Request) -> LinkGitHubAccountUseCase:
    return get_container(request).integrations.link_github_account


def get_sync_github_repository_use_case(request: Request) -> SyncGitHubRepositoryUseCase:
    return get_container(request).integrations.sync_github_repository


def get_execute_ephemeral_validation_use_case(request: Request) -> ExecuteEphemeralValidationUseCase:
    return get_container(request).integrations.execute_ephemeral_validation
