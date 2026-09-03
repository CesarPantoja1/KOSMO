from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from kosmo.application.integrations.recover_pending_deployments import recover_pending_deployments
from kosmo.contracts.integrations.deployment import DeploymentProvider, DeploymentStatus, ProjectDeployment
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.project import Project


def _project(project_id: ProjectId, owner_id: UserId) -> Project:
    return Project(
        id=project_id,
        name="Proyecto",
        slug="proyecto",
        description="",
        owner_id=owner_id,
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_recover_pending_deployments_resumes_only_valid_building_deployments() -> None:
    project_id = ProjectId("prj_pending")
    owner_id = UserId("usr_owner")
    pending = ProjectDeployment(
        project_id=project_id,
        provider=DeploymentProvider.RAILWAY,
        service_id="srv_pending",
        status=DeploymentStatus.BUILDING,
    )
    missing_service = ProjectDeployment(
        project_id=ProjectId("prj_without_service"),
        provider=DeploymentProvider.RAILWAY,
        status=DeploymentStatus.BUILDING,
    )
    deployment_repo = MagicMock()
    deployment_repo.list_by_status = AsyncMock(return_value=[pending, missing_service])
    project_repo = MagicMock()
    project_repo.by_id = AsyncMock(return_value=_project(project_id, owner_id))
    worker = MagicMock()

    recovered = await recover_pending_deployments(
        project_deployment_repo=deployment_repo,
        project_repo=project_repo,
        deployment_worker=worker,
    )

    assert recovered == 1
    deployment_repo.list_by_status.assert_awaited_once_with(DeploymentStatus.BUILDING)
    worker.start_monitoring.assert_called_once_with(
        project_id=project_id,
        user_id=owner_id,
        provider=DeploymentProvider.RAILWAY,
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_recover_pending_deployments_skips_deleted_project() -> None:
    deployment = ProjectDeployment(
        project_id=ProjectId("prj_deleted"),
        provider=DeploymentProvider.RAILWAY,
        service_id="srv_deleted",
        status=DeploymentStatus.BUILDING,
    )
    deployment_repo = MagicMock()
    deployment_repo.list_by_status = AsyncMock(return_value=[deployment])
    project_repo = MagicMock()
    project_repo.by_id = AsyncMock(return_value=None)
    worker = MagicMock()

    recovered = await recover_pending_deployments(
        project_deployment_repo=deployment_repo,
        project_repo=project_repo,
        deployment_worker=worker,
    )

    assert recovered == 0
    worker.start_monitoring.assert_not_called()
