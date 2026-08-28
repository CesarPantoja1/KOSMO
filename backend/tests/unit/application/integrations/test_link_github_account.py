from unittest.mock import AsyncMock, MagicMock

import pytest

from kosmo.application.integrations.link_github_account import (
    LinkGitHubAccountCommand,
    LinkGitHubAccountUseCase,
)
from kosmo.contracts.auth.principal import Principal
from kosmo.contracts.auth.secrets import EncryptedSecret
from kosmo.contracts.integrations.github import (
    GitHubOAuthToken,
    GitHubPermissionError,
    GitHubUser,
    UserGitHubIntegration,
)


@pytest.fixture
def mock_oauth_client():
    return AsyncMock()


@pytest.fixture
def mock_cipher():
    return MagicMock()


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def principal():
    return Principal(subject="user-1")


@pytest.fixture
def use_case(mock_oauth_client, mock_cipher, mock_repo):
    return LinkGitHubAccountUseCase(
        oauth_client=mock_oauth_client,
        cipher=mock_cipher,
        repo=mock_repo,
        client_id="test-client-id",
        client_secret="test-client-secret",
    )


async def test_link_github_account_success(
    use_case: LinkGitHubAccountUseCase,
    mock_oauth_client: AsyncMock,
    mock_cipher: MagicMock,
    mock_repo: AsyncMock,
    principal: Principal,
):
    cmd = LinkGitHubAccountCommand(code="temp-code")
    mock_oauth_client.exchange_oauth_code.return_value = GitHubOAuthToken(
        access_token="gho_test_token", scope="read:user,repo"
    )
    mock_oauth_client.get_authenticated_user.return_value = GitHubUser(login="octocat", id=1)
    mock_cipher.encrypt.return_value = EncryptedSecret(ciphertext=b"encrypted-bytes")

    await use_case.execute(principal, cmd)

    mock_oauth_client.exchange_oauth_code.assert_called_once_with(
        client_id="test-client-id",
        client_secret="test-client-secret",
        code="temp-code",
    )
    mock_oauth_client.get_authenticated_user.assert_called_once_with("gho_test_token")
    mock_cipher.encrypt.assert_called_once_with(b"gho_test_token")

    # Guardar entidad
    mock_repo.save.assert_called_once()
    integration: UserGitHubIntegration = mock_repo.save.call_args[0][0]
    assert integration.user_id == "user-1"
    assert integration.github_username == "octocat"
    assert integration.encrypted_token == "ZW5jcnlwdGVkLWJ5dGVz"  # base64(b"encrypted-bytes")


async def test_link_github_account_missing_repo_scope(
    use_case: LinkGitHubAccountUseCase,
    mock_oauth_client: AsyncMock,
    mock_repo: AsyncMock,
    principal: Principal,
):
    cmd = LinkGitHubAccountCommand(code="temp-code")
    mock_oauth_client.exchange_oauth_code.return_value = GitHubOAuthToken(
        access_token="gho_test_token", scope="read:user, gist"
    )

    with pytest.raises(GitHubPermissionError) as exc:
        await use_case.execute(principal, cmd)

    assert "repo" in str(exc.value)
    mock_repo.save.assert_not_called()
