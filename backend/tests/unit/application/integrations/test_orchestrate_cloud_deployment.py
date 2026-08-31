import base64
from unittest.mock import AsyncMock, MagicMock

import pytest

from kosmo.application.integrations.orchestrate_cloud_deployment import (
    OrchestrateCloudDeploymentCommand,
    OrchestrateCloudDeploymentUseCase,
    OrquestarDespliegueNubeCommand,
    OrquestarDespliegueNubeUseCase,
)
from kosmo.contracts.auth.principal import Principal
from kosmo.contracts.auth.secrets import EncryptedSecret
from kosmo.contracts.integrations.deployment import (
    DeploymentAccountNotLinkedError,
    DeploymentAuthenticationError,
    DeploymentProvider,
    DeploymentRepositoryMissingError,
    DeploymentStatus,
    ProjectDeployment,
    UserDeploymentIntegration,
    VolumeConfig,
)
from kosmo.contracts.integrations.github import (
    GitHubSyncStatus,
    ProjectGitHubIntegration,
)
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.infrastructure.security.fernet_vault import FernetSecretCipher
from tests.unit.fakes import (
    InMemoryProjectDeploymentRepository,
    InMemoryProjectGitHubIntegrationRepository,
    InMemoryUserDeploymentIntegrationRepository,
)


@pytest.fixture
def mock_project_deployment_repo():
    return AsyncMock()


@pytest.fixture
def mock_user_deployment_repo():
    return AsyncMock()


@pytest.fixture
def mock_project_github_repo():
    return AsyncMock()


@pytest.fixture
def mock_deployment_client():
    return AsyncMock()


@pytest.fixture
def mock_cipher():
    return MagicMock()


@pytest.fixture
def principal():
    return Principal(subject="usr_deployer_01")


@pytest.fixture
def use_case(
    mock_project_deployment_repo,
    mock_user_deployment_repo,
    mock_project_github_repo,
    mock_deployment_client,
    mock_cipher,
):
    return OrchestrateCloudDeploymentUseCase(
        project_deployment_repo=mock_project_deployment_repo,
        user_deployment_repo=mock_user_deployment_repo,
        project_github_repo=mock_project_github_repo,
        deployment_client=mock_deployment_client,
        cipher=mock_cipher,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrate_deployment_success_initial(
    use_case: OrchestrateCloudDeploymentUseCase,
    mock_project_deployment_repo: AsyncMock,
    mock_user_deployment_repo: AsyncMock,
    mock_project_github_repo: AsyncMock,
    mock_deployment_client: AsyncMock,
    mock_cipher: MagicMock,
    principal: Principal,
):
    # Arrange
    project_id = ProjectId("prj_inventory_01")
    cmd = OrchestrateCloudDeploymentCommand(
        project_id=project_id,
        environment_variables={"CUSTOM_VAR": "custom_val"},
    )

    # 1. User integration exists with encrypted token
    mock_user_deployment_repo.get_by_user_id.return_value = UserDeploymentIntegration(
        user_id=UserId(principal.subject),
        provider=DeploymentProvider.RAILWAY,
        encrypted_token=base64.b64encode(b"ciphertext_rw").decode("utf-8"),
    )
    mock_cipher.decrypt.return_value = b"decrypted_railway_token"

    # 2. GitHub repo exists and is synced
    mock_project_github_repo.get_by_project_id.return_value = ProjectGitHubIntegration(
        project_id=project_id,
        repo_name="inventory-app",
        repo_url="https://github.com/octocat/inventory-app",
        sync_status=GitHubSyncStatus.SYNCED,
    )

    # 3. No existing deployment in Railway
    mock_project_deployment_repo.get_by_project_id.return_value = None

    # 4. Railway client responses
    mock_deployment_client.create_service.return_value = "srv_railway_999"
    mock_deployment_client.configure_volume.return_value = None
    mock_deployment_client.trigger_deployment.return_value = None

    # Act
    result = await use_case.execute(principal, cmd)

    # Assert
    mock_user_deployment_repo.get_by_user_id.assert_called_once_with(
        UserId("usr_deployer_01"), DeploymentProvider.RAILWAY
    )
    mock_cipher.decrypt.assert_called_once_with(EncryptedSecret(ciphertext=b"ciphertext_rw"))
    mock_project_github_repo.get_by_project_id.assert_called_once_with(project_id)

    # Verifica llamadas a Railway client
    mock_deployment_client.create_service.assert_called_once()
    create_call_args = mock_deployment_client.create_service.call_args[1]
    assert create_call_args["token"] == "decrypted_railway_token"
    assert create_call_args["repo_url"] == "https://github.com/octocat/inventory-app"
    assert any(ev.key == "CUSTOM_VAR" and ev.value == "custom_val" for ev in create_call_args["env_vars"])
    assert any(ev.key == "DATABASE_URL" and ev.value == "file:/data/db.sqlite" for ev in create_call_args["env_vars"])

    mock_deployment_client.configure_volume.assert_called_once_with(
        token="decrypted_railway_token",
        service_id="srv_railway_999",
        volume=VolumeConfig(mount_path="/data", size_mb=512),
    )
    mock_deployment_client.trigger_deployment.assert_called_once_with(
        token="decrypted_railway_token",
        service_id="srv_railway_999",
    )

    # Persistencia
    mock_project_deployment_repo.save.assert_called_once()
    saved: ProjectDeployment = mock_project_deployment_repo.save.call_args[0][0]
    assert saved.project_id == project_id
    assert saved.provider == DeploymentProvider.RAILWAY
    assert saved.service_id == "srv_railway_999"
    assert saved.status == DeploymentStatus.BUILDING
    assert result == saved


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrate_deployment_reuses_existing_service_id(
    use_case: OrchestrateCloudDeploymentUseCase,
    mock_project_deployment_repo: AsyncMock,
    mock_user_deployment_repo: AsyncMock,
    mock_project_github_repo: AsyncMock,
    mock_deployment_client: AsyncMock,
    mock_cipher: MagicMock,
    principal: Principal,
):
    # Arrange
    project_id = ProjectId("prj_existing_01")
    cmd = OrchestrateCloudDeploymentCommand(project_id=project_id)

    mock_user_deployment_repo.get_by_user_id.return_value = UserDeploymentIntegration(
        user_id=UserId(principal.subject),
        provider=DeploymentProvider.RAILWAY,
        encrypted_token=base64.b64encode(b"ciphertext_rw").decode("utf-8"),
    )
    mock_cipher.decrypt.return_value = b"decrypted_token"

    mock_project_github_repo.get_by_project_id.return_value = ProjectGitHubIntegration(
        project_id=project_id,
        repo_name="inventory-app",
        repo_url="https://github.com/octocat/inventory-app",
        sync_status=GitHubSyncStatus.SYNCED,
    )

    # Existing deployment with already created service
    mock_project_deployment_repo.get_by_project_id.return_value = ProjectDeployment(
        project_id=project_id,
        provider=DeploymentProvider.RAILWAY,
        service_id="srv_already_existing_123",
        status=DeploymentStatus.PUBLISHED,
        public_url="https://inventory.up.railway.app",
    )

    # Act
    result = await use_case.execute(principal, cmd)

    # Assert
    # No vuelve a llamar create_service, reutiliza srv_already_existing_123
    mock_deployment_client.create_service.assert_not_called()
    mock_deployment_client.configure_volume.assert_called_once_with(
        token="decrypted_token",
        service_id="srv_already_existing_123",
        volume=VolumeConfig(mount_path="/data", size_mb=512),
    )
    mock_deployment_client.trigger_deployment.assert_called_once_with(
        token="decrypted_token",
        service_id="srv_already_existing_123",
    )
    assert result.service_id == "srv_already_existing_123"
    assert result.status == DeploymentStatus.BUILDING


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrate_deployment_raises_when_account_not_linked(
    use_case: OrchestrateCloudDeploymentUseCase,
    mock_user_deployment_repo: AsyncMock,
    principal: Principal,
):
    # Arrange
    cmd = OrchestrateCloudDeploymentCommand(project_id=ProjectId("prj_01"))
    mock_user_deployment_repo.get_by_user_id.return_value = None

    # Act & Assert
    with pytest.raises(DeploymentAccountNotLinkedError, match="no está vinculada"):
        await use_case.execute(principal, cmd)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrate_deployment_raises_when_github_repo_missing(
    use_case: OrchestrateCloudDeploymentUseCase,
    mock_user_deployment_repo: AsyncMock,
    mock_project_github_repo: AsyncMock,
    mock_cipher: MagicMock,
    principal: Principal,
):
    # Arrange
    cmd = OrchestrateCloudDeploymentCommand(project_id=ProjectId("prj_01"))
    mock_user_deployment_repo.get_by_user_id.return_value = UserDeploymentIntegration(
        user_id=UserId(principal.subject),
        provider=DeploymentProvider.RAILWAY,
        encrypted_token=base64.b64encode(b"ciphertext").decode("utf-8"),
    )
    mock_cipher.decrypt.return_value = b"token"
    mock_project_github_repo.get_by_project_id.return_value = None

    # Act & Assert
    with pytest.raises(DeploymentRepositoryMissingError, match="no cuenta con un repositorio remoto de GitHub"):
        await use_case.execute(principal, cmd)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrate_deployment_raises_when_github_repo_not_created(
    use_case: OrchestrateCloudDeploymentUseCase,
    mock_user_deployment_repo: AsyncMock,
    mock_project_github_repo: AsyncMock,
    mock_cipher: MagicMock,
    principal: Principal,
):
    # Arrange
    cmd = OrchestrateCloudDeploymentCommand(project_id=ProjectId("prj_01"))
    mock_user_deployment_repo.get_by_user_id.return_value = UserDeploymentIntegration(
        user_id=UserId(principal.subject),
        provider=DeploymentProvider.RAILWAY,
        encrypted_token=base64.b64encode(b"ciphertext").decode("utf-8"),
    )
    mock_cipher.decrypt.return_value = b"token"
    mock_project_github_repo.get_by_project_id.return_value = ProjectGitHubIntegration(
        project_id=ProjectId("prj_01"),
        sync_status=GitHubSyncStatus.NOT_CREATED,
        repo_url="",
    )

    # Act & Assert
    with pytest.raises(DeploymentRepositoryMissingError, match="no cuenta con un repositorio remoto de GitHub"):
        await use_case.execute(principal, cmd)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrate_deployment_handles_decryption_failure(
    use_case: OrchestrateCloudDeploymentUseCase,
    mock_user_deployment_repo: AsyncMock,
    mock_cipher: MagicMock,
    principal: Principal,
):
    # Arrange
    cmd = OrchestrateCloudDeploymentCommand(project_id=ProjectId("prj_01"))
    mock_user_deployment_repo.get_by_user_id.return_value = UserDeploymentIntegration(
        user_id=UserId(principal.subject),
        provider=DeploymentProvider.RAILWAY,
        encrypted_token="corrupted-base64",
    )
    mock_cipher.decrypt.side_effect = Exception("Decryption error")

    # Act & Assert
    with pytest.raises(DeploymentAuthenticationError, match="Error al descifrar"):
        await use_case.execute(principal, cmd)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrate_deployment_full_integration_with_fakes():
    # Arrange
    master_key = FernetSecretCipher.generate_master_key()
    cipher = FernetSecretCipher(master_key)

    user_repo = InMemoryUserDeploymentIntegrationRepository()
    project_repo = InMemoryProjectDeploymentRepository()
    github_repo = InMemoryProjectGitHubIntegrationRepository()

    principal = Principal(subject="usr_full_test")
    project_id = ProjectId("prj_full_test")

    # Seed user integration
    enc = cipher.encrypt(b"secret-railway-api-token")
    enc_token = base64.b64encode(enc.ciphertext).decode("utf-8")
    await user_repo.save(
        UserDeploymentIntegration(
            user_id=UserId("usr_full_test"),
            provider=DeploymentProvider.RAILWAY,
            encrypted_token=enc_token,
        )
    )

    # Seed GitHub integration
    await github_repo.save(
        ProjectGitHubIntegration(
            project_id=project_id,
            repo_name="my-cool-app",
            repo_url="https://github.com/octocat/my-cool-app",
            sync_status=GitHubSyncStatus.SYNCED,
        )
    )

    mock_client = AsyncMock()
    mock_client.create_service.return_value = "srv_live_123"

    use_case = OrquestarDespliegueNubeUseCase(
        project_deployment_repo=project_repo,
        user_deployment_repo=user_repo,
        project_github_repo=github_repo,
        deployment_client=mock_client,
        cipher=cipher,
    )

    # Act
    cmd = OrquestarDespliegueNubeCommand(project_id=project_id)
    deployment = await use_case.execute(principal, cmd)

    # Assert
    assert deployment.service_id == "srv_live_123"
    assert deployment.status == DeploymentStatus.BUILDING

    # Check persistence
    persisted = await project_repo.get_by_project_id(project_id)
    assert persisted is not None
    assert persisted.service_id == "srv_live_123"
    assert persisted.status == DeploymentStatus.BUILDING
