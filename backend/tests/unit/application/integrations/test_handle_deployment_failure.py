from unittest.mock import AsyncMock

import pytest

from kosmo.application.integrations.handle_deployment_failure import (
    HandleDeploymentFailureCommand,
    HandleDeploymentFailureUseCase,
)
from kosmo.contracts.integrations.deployment import (
    DeploymentProvider,
    DeploymentStatus,
    ProjectDeployment,
)
from kosmo.contracts.sdd.ids import ProjectId


@pytest.fixture
def project_deployment_repo():
    return AsyncMock()


@pytest.fixture
def use_case(project_deployment_repo):
    return HandleDeploymentFailureUseCase(project_deployment_repo=project_deployment_repo)


async def test_handle_deployment_failure_existing_deployment(
    use_case: HandleDeploymentFailureUseCase,
    project_deployment_repo: AsyncMock,
):
    cmd = HandleDeploymentFailureCommand(
        project_id=ProjectId("proj-1"),
        error_message="Runtime error on Railway",
        build_logs_url="https://railway.app/logs/123",
    )

    project_deployment_repo.get_by_project_id.return_value = ProjectDeployment(
        project_id=ProjectId("proj-1"),
        provider=DeploymentProvider.RAILWAY,
        service_id="srv-123",
        status=DeploymentStatus.BUILDING,
        build_logs_url="https://railway.app/logs/old",
    )

    result = await use_case.execute(cmd)

    assert result.status == DeploymentStatus.FAILED
    assert result.error_message == "Runtime error on Railway"
    assert result.build_logs_url == "https://railway.app/logs/123"
    project_deployment_repo.save.assert_called_once_with(result)


async def test_handle_deployment_failure_non_existing_deployment(
    use_case: HandleDeploymentFailureUseCase,
    project_deployment_repo: AsyncMock,
):
    cmd = HandleDeploymentFailureCommand(
        project_id=ProjectId("proj-2"),
        error_message="Creation failed early",
        provider=DeploymentProvider.RAILWAY,
    )

    project_deployment_repo.get_by_project_id.return_value = None

    result = await use_case.execute(cmd)

    assert result.status == DeploymentStatus.FAILED
    assert result.error_message == "Creation failed early"
    assert result.build_logs_url is None
    project_deployment_repo.save.assert_called_once_with(result)
