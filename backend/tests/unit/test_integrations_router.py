from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Request

from kosmo.application.integrations.link_deployment_provider import (
    LinkDeploymentPlatformCommand,
    LinkDeploymentPlatformUseCase,
)
from kosmo.application.integrations.link_github_account import (
    LinkGitHubAccountCommand,
    LinkGitHubAccountUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.integrations.deployment import (
    DeploymentApiError,
    DeploymentProvider,
    UserDeploymentIntegration,
)
from kosmo.contracts.integrations.github import (
    GitHubAuthenticationError,
    UserGitHubIntegration,
)
from kosmo.contracts.sdd.ids import UserId
from kosmo.infrastructure.api.composition import AppContainer
from kosmo.infrastructure.api.routers.integrations import (
    connect_oauth,
    disconnect_integration,
    get_integration_status,
)
from kosmo.infrastructure.api.schemas import ConnectOAuthRequest


def _principal(subject: str = "usr_123") -> Principal:
    return Principal(subject=subject, scopes=frozenset({"*"}))


def _mock_request(
    user_integration: UserGitHubIntegration | None = None,
    deployment_integration: UserDeploymentIntegration | None = None,
) -> Request:
    req = MagicMock(spec=Request)
    container = MagicMock(spec=AppContainer)
    user_repo = AsyncMock()
    user_repo.get_by_user_id.return_value = user_integration
    user_repo.delete_by_user_id.return_value = True
    container.repos.user_github_integrations = user_repo

    deploy_repo = AsyncMock()
    deploy_repo.get_by_user_id.return_value = deployment_integration
    deploy_repo.delete_by_user_id.return_value = True
    container.repos.user_deployment_integrations = deploy_repo

    req.app.state.container = container
    return req


@pytest.mark.asyncio
@pytest.mark.unit
async def test_connect_oauth_github_success_200() -> None:
    # Arrange
    use_case = AsyncMock(spec=LinkGitHubAccountUseCase)
    railway_use_case = AsyncMock(spec=LinkDeploymentPlatformUseCase)
    now = datetime.now(UTC)
    use_case.execute.return_value = UserGitHubIntegration(
        user_id=UserId("usr_123"),
        github_username="octocat",
        encrypted_token="encrypted_secret_token",
        updated_at=now,
    )
    body = ConnectOAuthRequest(
        code="gho_valid_code_123",
        redirect_uri="http://localhost:3000",
        code_verifier="v" * 64,
    )

    # Act
    response = await connect_oauth(
        provider="github",
        body=body,
        principal=_principal("usr_123"),
        github_use_case=use_case,
        railway_use_case=railway_use_case,
    )

    # Assert
    assert response.provider == "github"
    assert response.is_connected is True
    assert response.username == "octocat"
    assert response.connected_at == now
    use_case.execute.assert_called_once_with(
        _principal("usr_123"),
        LinkGitHubAccountCommand(
            code="gho_valid_code_123",
            redirect_uri="http://localhost:3000",
            code_verifier="v" * 64,
        ),
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_connect_oauth_railway_success_200() -> None:
    # Arrange
    github_use_case = AsyncMock(spec=LinkGitHubAccountUseCase)
    railway_use_case = AsyncMock(spec=LinkDeploymentPlatformUseCase)
    now = datetime.now(UTC)
    railway_use_case.execute.return_value = UserDeploymentIntegration(
        user_id=UserId("usr_123"),
        provider=DeploymentProvider.RAILWAY,
        provider_username="railway_user",
        encrypted_token="encrypted_railway_token",
        updated_at=now,
    )
    body = ConnectOAuthRequest(code="rw_code_123", code_verifier="v" * 64)

    # Act
    response = await connect_oauth(
        provider="railway",
        body=body,
        principal=_principal("usr_123"),
        github_use_case=github_use_case,
        railway_use_case=railway_use_case,
    )

    # Assert
    assert response.provider == "railway"
    assert response.is_connected is True
    assert response.username == "railway_user"
    assert response.connected_at == now
    railway_use_case.execute.assert_called_once_with(
        _principal("usr_123"),
        LinkDeploymentPlatformCommand(
            code="rw_code_123",
            provider=DeploymentProvider.RAILWAY,
            code_verifier="v" * 64,
        ),
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_connect_oauth_unsupported_provider_400() -> None:
    # Arrange
    github_use_case = AsyncMock(spec=LinkGitHubAccountUseCase)
    railway_use_case = AsyncMock(spec=LinkDeploymentPlatformUseCase)
    body = ConnectOAuthRequest(code="code123")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await connect_oauth(
            provider="unsupported_provider",
            body=body,
            principal=_principal(),
            github_use_case=github_use_case,
            railway_use_case=railway_use_case,
        )

    assert exc_info.value.status_code == 400
    assert "no soportado" in exc_info.value.detail


@pytest.mark.asyncio
@pytest.mark.unit
async def test_connect_oauth_github_auth_error_400() -> None:
    # Arrange
    use_case = AsyncMock(spec=LinkGitHubAccountUseCase)
    railway_use_case = AsyncMock(spec=LinkDeploymentPlatformUseCase)
    use_case.execute.side_effect = GitHubAuthenticationError("Código de autorización OAuth inválido o expirado")
    body = ConnectOAuthRequest(code="gho_expired_code")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await connect_oauth(
            provider="github",
            body=body,
            principal=_principal(),
            github_use_case=use_case,
            railway_use_case=railway_use_case,
        )

    assert exc_info.value.status_code == 400
    assert "inválido o expirado" in exc_info.value.detail


@pytest.mark.asyncio
@pytest.mark.unit
async def test_connect_oauth_railway_api_error_502() -> None:
    # Arrange
    github_use_case = AsyncMock(spec=LinkGitHubAccountUseCase)
    railway_use_case = AsyncMock(spec=LinkDeploymentPlatformUseCase)
    railway_use_case.execute.side_effect = DeploymentApiError("Error de comunicación con Railway API")
    body = ConnectOAuthRequest(code="rw_bad_code")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await connect_oauth(
            provider="railway",
            body=body,
            principal=_principal(),
            github_use_case=github_use_case,
            railway_use_case=railway_use_case,
        )

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_integration_status_github_connected_200() -> None:
    # Arrange
    now = datetime.now(UTC)
    integration = UserGitHubIntegration(
        user_id=UserId("usr_123"),
        github_username="octocat",
        encrypted_token="enc_token",
        updated_at=now,
    )
    request = _mock_request(user_integration=integration)

    # Act
    response = await get_integration_status(
        provider="github",
        request=request,
        principal=_principal("usr_123"),
    )

    # Assert
    assert response.provider == "github"
    assert response.is_connected is True
    assert response.username == "octocat"
    assert response.connected_at == now


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_integration_status_railway_connected_200() -> None:
    # Arrange
    now = datetime.now(UTC)
    deployment_int = UserDeploymentIntegration(
        user_id=UserId("usr_123"),
        provider=DeploymentProvider.RAILWAY,
        provider_username="railway_user",
        encrypted_token="enc_token",
        updated_at=now,
    )
    request = _mock_request(deployment_integration=deployment_int)

    # Act
    response = await get_integration_status(
        provider="railway",
        request=request,
        principal=_principal("usr_123"),
    )

    # Assert
    assert response.provider == "railway"
    assert response.is_connected is True
    assert response.username == "railway_user"
    assert response.connected_at == now


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_integration_status_not_connected_200() -> None:
    # Arrange
    request = _mock_request(user_integration=None)

    # Act
    response = await get_integration_status(
        provider="github",
        request=request,
        principal=_principal("usr_123"),
    )

    # Assert
    assert response.provider == "github"
    assert response.is_connected is False
    assert response.username is None
    assert response.connected_at is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_disconnect_integration_github_success_204() -> None:
    # Arrange
    integration = UserGitHubIntegration(
        user_id=UserId("usr_123"),
        github_username="octocat",
        encrypted_token="enc_token",
    )
    request = _mock_request(user_integration=integration)

    # Act
    response = await disconnect_integration(
        provider="github",
        request=request,
        principal=_principal("usr_123"),
    )

    assert response.status_code == 204
    request.app.state.container.repos.user_github_integrations.delete_by_user_id.assert_called_once_with(
        UserId("usr_123")
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_disconnect_integration_railway_success_204() -> None:
    # Arrange
    deployment_int = UserDeploymentIntegration(
        user_id=UserId("usr_123"),
        provider=DeploymentProvider.RAILWAY,
        provider_username="rw_user",
        encrypted_token="enc_token",
    )
    request = _mock_request(deployment_integration=deployment_int)

    # Act
    response = await disconnect_integration(
        provider="railway",
        request=request,
        principal=_principal("usr_123"),
    )

    assert response.status_code == 204
    request.app.state.container.repos.user_deployment_integrations.delete_by_user_id.assert_called_once_with(
        UserId("usr_123"), DeploymentProvider.RAILWAY
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_disconnect_integration_not_found_404() -> None:
    # Arrange
    request = _mock_request(user_integration=None)

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await disconnect_integration(
            provider="github",
            request=request,
            principal=_principal("usr_123"),
        )

    assert exc_info.value.status_code == 404
