import base64
from unittest.mock import AsyncMock, MagicMock

import pytest

from kosmo.application.integrations.monitor_deployment_status import (
    MonitorDeploymentStatusCommand,
    MonitorDeploymentStatusUseCase,
)
from kosmo.contracts.auth.secrets import EncryptedSecret
from kosmo.contracts.integrations.deployment import (
    DeploymentProvider,
    DeploymentStatus,
    ProjectDeployment,
    UserDeploymentIntegration,
)
from kosmo.contracts.sdd.ids import ProjectId, UserId


@pytest.fixture
def project_deployment_repo():
    return AsyncMock()


@pytest.fixture
def user_deployment_repo():
    return AsyncMock()


@pytest.fixture
def deployment_client():
    return AsyncMock()


@pytest.fixture
def cipher():
    return MagicMock()


@pytest.fixture
def use_case(
    project_deployment_repo,
    user_deployment_repo,
    deployment_client,
    cipher,
):
    return MonitorDeploymentStatusUseCase(
        project_deployment_repo=project_deployment_repo,
        user_deployment_repo=user_deployment_repo,
        deployment_client=deployment_client,
        cipher=cipher,
    )


async def test_monitor_deployment_success_transition(
    use_case: MonitorDeploymentStatusUseCase,
    project_deployment_repo: AsyncMock,
    user_deployment_repo: AsyncMock,
    deployment_client: AsyncMock,
    cipher: MagicMock,
):
    cmd = MonitorDeploymentStatusCommand(
        project_id=ProjectId("proj-1"),
        user_id=UserId("user-1"),
        max_attempts=3,
        delay_seconds=0,
    )

    project_deployment_repo.get_by_project_id.return_value = ProjectDeployment(
        project_id=ProjectId("proj-1"),
        provider=DeploymentProvider.RAILWAY,
        service_id="srv-123",
        status=DeploymentStatus.BUILDING,
    )

    user_deployment_repo.get_by_user_id.return_value = UserDeploymentIntegration(
        user_id=UserId("user-1"),
        provider=DeploymentProvider.RAILWAY,
        encrypted_token=base64.b64encode(b"enc").decode("utf-8"),
    )
    cipher.decrypt.return_value = b"real-token"

    # Simular que en el primer intento sigue "BUILDING", y en el segundo cambia a "PUBLISHED"
    deployment_client.get_service_status.side_effect = [
        (DeploymentStatus.BUILDING, None, None),
        (DeploymentStatus.PUBLISHED, "https://app.example.com", None),
    ]

    await use_case.execute(cmd)

    # El token se desencripta 1 vez
    cipher.decrypt.assert_called_once_with(EncryptedSecret(ciphertext=b"enc"))

    # get_service_status se llama 2 veces
    assert deployment_client.get_service_status.call_count == 2

    # Se guarda el deployment sÃ³lo cuando cambia de estado (en la segunda iteraciÃ³n)
    project_deployment_repo.save.assert_called_once()
    saved_deployment = project_deployment_repo.save.call_args[0][0]
    assert saved_deployment.status == DeploymentStatus.PUBLISHED
    assert saved_deployment.public_url == "https://app.example.com"


async def test_monitor_deployment_fails_transition(
    use_case: MonitorDeploymentStatusUseCase,
    project_deployment_repo: AsyncMock,
    user_deployment_repo: AsyncMock,
    deployment_client: AsyncMock,
    cipher: MagicMock,
):
    cmd = MonitorDeploymentStatusCommand(
        project_id=ProjectId("proj-1"),
        user_id=UserId("user-1"),
        max_attempts=2,
        delay_seconds=0,
    )

    project_deployment_repo.get_by_project_id.return_value = ProjectDeployment(
        project_id=ProjectId("proj-1"),
        provider=DeploymentProvider.RAILWAY,
        service_id="srv-123",
        status=DeploymentStatus.BUILDING,
    )

    user_deployment_repo.get_by_user_id.return_value = UserDeploymentIntegration(
        user_id=UserId("user-1"),
        provider=DeploymentProvider.RAILWAY,
        encrypted_token=base64.b64encode(b"enc").decode("utf-8"),
    )
    cipher.decrypt.return_value = b"real-token"

    # Falla en el primer intento
    deployment_client.get_service_status.return_value = (
        DeploymentStatus.FAILED,
        None,
        "Build failed due to syntax error",
    )

    await use_case.execute(cmd)

    project_deployment_repo.save.assert_called_once()
    saved_deployment = project_deployment_repo.save.call_args[0][0]
    assert saved_deployment.status == DeploymentStatus.FAILED
    assert saved_deployment.build_logs_url == "Build failed due to syntax error"
    assert saved_deployment.error_message == "Build failed due to syntax error"


async def test_monitor_deployment_max_attempts(
    use_case: MonitorDeploymentStatusUseCase,
    project_deployment_repo: AsyncMock,
    user_deployment_repo: AsyncMock,
    deployment_client: AsyncMock,
    cipher: MagicMock,
):
    cmd = MonitorDeploymentStatusCommand(
        project_id=ProjectId("proj-1"),
        user_id=UserId("user-1"),
        max_attempts=3,
        delay_seconds=0,
    )

    project_deployment_repo.get_by_project_id.return_value = ProjectDeployment(
        project_id=ProjectId("proj-1"),
        provider=DeploymentProvider.RAILWAY,
        service_id="srv-123",
        status=DeploymentStatus.BUILDING,
    )

    user_deployment_repo.get_by_user_id.return_value = UserDeploymentIntegration(
        user_id=UserId("user-1"),
        provider=DeploymentProvider.RAILWAY,
        encrypted_token=base64.b64encode(b"enc").decode("utf-8"),
    )
    cipher.decrypt.return_value = b"real-token"

    # Siempre devuelve BUILDING
    deployment_client.get_service_status.return_value = (DeploymentStatus.BUILDING, None, None)

    await use_case.execute(cmd)

    # get_service_status se llama 3 veces (max_attempts)
    assert deployment_client.get_service_status.call_count == 3

    # Nunca se guarda porque el estado no cambia
    project_deployment_repo.save.assert_not_called()
