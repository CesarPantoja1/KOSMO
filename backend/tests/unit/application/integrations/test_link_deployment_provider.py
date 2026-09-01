from unittest.mock import AsyncMock, MagicMock

import pytest

from kosmo.application.integrations.link_deployment_provider import (
    LinkDeploymentPlatformCommand,
    LinkDeploymentPlatformUseCase,
    LinkDeploymentProviderCommand,
    LinkDeploymentProviderUseCase,
)
from kosmo.contracts.auth.principal import Principal
from kosmo.contracts.auth.secrets import EncryptedSecret
from kosmo.contracts.integrations.deployment import (
    DeploymentAuthenticationError,
    DeploymentOAuthToken,
    DeploymentProvider,
    UserDeploymentIntegration,
)
from kosmo.infrastructure.security.fernet_vault import FernetSecretCipher
from tests.unit.fakes import InMemoryUserDeploymentIntegrationRepository


@pytest.fixture
def mock_deployment_client():
    return AsyncMock()


@pytest.fixture
def mock_cipher():
    return MagicMock()


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def principal():
    return Principal(subject="user-deploy-1")


@pytest.fixture
def use_case(mock_deployment_client, mock_cipher, mock_repo):
    return LinkDeploymentPlatformUseCase(
        deployment_client=mock_deployment_client,
        cipher=mock_cipher,
        repo=mock_repo,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_link_deployment_platform_success(
    use_case: LinkDeploymentPlatformUseCase,
    mock_deployment_client: AsyncMock,
    mock_cipher: MagicMock,
    mock_repo: AsyncMock,
    principal: Principal,
):
    # Arrange
    cmd = LinkDeploymentPlatformCommand(code="temp-oauth-code")
    mock_deployment_client.exchange_oauth_code.return_value = DeploymentOAuthToken(
        access_token="rw_token_xyz",
        token_type="bearer",
        scope="project:write",
    )
    mock_cipher.encrypt.return_value = EncryptedSecret(ciphertext=b"encrypted-deployment-token")

    # Act
    result = await use_case.execute(principal, cmd)

    # Assert
    mock_deployment_client.exchange_oauth_code.assert_called_once_with("temp-oauth-code", None)
    mock_cipher.encrypt.assert_called_once_with(b"rw_token_xyz")
    mock_repo.save.assert_called_once()
    saved_integration: UserDeploymentIntegration = mock_repo.save.call_args[0][0]
    assert saved_integration.user_id == "user-deploy-1"
    assert saved_integration.provider == DeploymentProvider.RAILWAY
    assert saved_integration.encrypted_token == "ZW5jcnlwdGVkLWRlcGxveW1lbnQtdG9rZW4="
    assert result == saved_integration


@pytest.mark.unit
@pytest.mark.asyncio
async def test_link_deployment_platform_with_redirect_uri_and_refresh_token(
    use_case: LinkDeploymentPlatformUseCase,
    mock_deployment_client: AsyncMock,
    mock_cipher: MagicMock,
    mock_repo: AsyncMock,
    principal: Principal,
):
    # Arrange
    cmd = LinkDeploymentPlatformCommand(
        code="auth-code-abc",
        redirect_uri="https://kosmo.app/perfil",
    )
    mock_deployment_client.exchange_oauth_code.return_value = DeploymentOAuthToken(
        access_token="access_123",
        refresh_token="refresh_456",
        scope="openid email profile workspace:admin",
    )
    mock_deployment_client.get_authenticated_user.return_value = {
        "name": "Jane Developer",
        "email": "jane@example.com",
    }
    mock_cipher.encrypt.side_effect = [
        EncryptedSecret(ciphertext=b"enc_access"),
        EncryptedSecret(ciphertext=b"enc_refresh"),
    ]

    # Act
    result = await use_case.execute(principal, cmd)

    # Assert
    mock_deployment_client.exchange_oauth_code.assert_called_once_with(
        "auth-code-abc",
        "https://kosmo.app/perfil",
    )
    mock_deployment_client.get_authenticated_user.assert_called_once_with("access_123")
    mock_repo.save.assert_called_once()
    saved: UserDeploymentIntegration = mock_repo.save.call_args[0][0]
    assert saved.provider_username == "Jane Developer"
    assert saved.encrypted_refresh_token is not None
    assert "workspace:admin" in saved.scopes
    assert result.provider_username == "Jane Developer"
    assert result.encrypted_refresh_token is not None
    assert "workspace:admin" in result.scopes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_link_deployment_platform_empty_code_raises_auth_error(
    use_case: LinkDeploymentPlatformUseCase,
    mock_deployment_client: AsyncMock,
    mock_repo: AsyncMock,
    principal: Principal,
):
    # Arrange
    cmd = LinkDeploymentPlatformCommand(code="   ")

    # Act & Assert
    with pytest.raises(DeploymentAuthenticationError, match="El código de autorización OAuth no puede estar vacío"):
        await use_case.execute(principal, cmd)

    mock_deployment_client.exchange_oauth_code.assert_not_called()
    mock_repo.save.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_link_deployment_platform_empty_token_raises_auth_error(
    use_case: LinkDeploymentPlatformUseCase,
    mock_deployment_client: AsyncMock,
    mock_repo: AsyncMock,
    principal: Principal,
):
    # Arrange
    cmd = LinkDeploymentPlatformCommand(code="valid-code")
    mock_deployment_client.exchange_oauth_code.return_value = DeploymentOAuthToken(access_token="")

    # Act & Assert
    with pytest.raises(DeploymentAuthenticationError, match="No se recibió un access_token válido"):
        await use_case.execute(principal, cmd)

    mock_repo.save.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_link_deployment_platform_with_fernet_and_in_memory_repo():
    # Arrange
    master_key = FernetSecretCipher.generate_master_key()
    cipher = FernetSecretCipher(master_key)
    repo = InMemoryUserDeploymentIntegrationRepository()
    mock_client = AsyncMock()
    mock_client.exchange_oauth_code.return_value = DeploymentOAuthToken(access_token="secret-token-12345")
    mock_client.get_authenticated_user.return_value = {"name": "Test User", "email": "test@user.com"}

    use_case = LinkDeploymentProviderUseCase(
        deployment_client=mock_client,
        cipher=cipher,
        repo=repo,
    )
    principal = Principal(subject="usr_real_fernet")
    cmd = LinkDeploymentProviderCommand(code="auth_code_999")

    # Act
    integration = await use_case.execute(principal, cmd)

    # Assert
    assert integration.user_id == "usr_real_fernet"
    assert integration.provider == DeploymentProvider.RAILWAY
    # Verificar descifrado
    import base64

    raw_ciphertext = base64.b64decode(integration.encrypted_token.encode("utf-8"))
    decrypted = cipher.decrypt(EncryptedSecret(ciphertext=raw_ciphertext)).decode("utf-8")
    assert decrypted == "secret-token-12345"

    # Verificar que persiste en repo
    saved = await repo.get_by_user_id("usr_real_fernet", DeploymentProvider.RAILWAY)
    assert saved is not None
    assert saved.user_id == "usr_real_fernet"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_link_deployment_platform_client_error_propagates(
    use_case: LinkDeploymentPlatformUseCase,
    mock_deployment_client: AsyncMock,
    mock_repo: AsyncMock,
    principal: Principal,
):
    # Arrange
    cmd = LinkDeploymentPlatformCommand(code="bad-code")
    mock_deployment_client.exchange_oauth_code.side_effect = DeploymentAuthenticationError("Código inválido")

    # Act & Assert
    with pytest.raises(DeploymentAuthenticationError, match="Código inválido"):
        await use_case.execute(principal, cmd)

    mock_repo.save.assert_not_called()
