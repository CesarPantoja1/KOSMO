from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from kosmo.application.integrations.handle_deployment_failure import (
    HandleDeploymentFailureCommand,
    HandleDeploymentFailureUseCase,
)
from kosmo.application.integrations.monitor_deployment_status import (
    MonitorDeploymentStatusCommand,
    MonitorDeploymentStatusUseCase,
)
from kosmo.contracts.integrations.deployment import DeploymentProvider
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.infrastructure.integrations.deployment_worker import DeploymentPollingWorker


@pytest.mark.asyncio
async def test_start_monitoring_runs_successfully() -> None:
    # Arrange
    mock_monitor = AsyncMock(spec=MonitorDeploymentStatusUseCase)
    mock_failure = AsyncMock(spec=HandleDeploymentFailureUseCase)

    worker = DeploymentPollingWorker(
        monitor_use_case=mock_monitor,
        failure_handler=mock_failure,
    )

    project_id = ProjectId("prj_01HTXYZ123456")
    user_id = UserId("usr_01HTABC987654")

    # Act
    task = worker.start_monitoring(
        project_id=project_id,
        user_id=user_id,
        max_attempts=5,
        delay_seconds=1,
    )

    assert worker.is_monitoring(project_id) is True
    await task

    # Assert
    assert worker.is_monitoring(project_id) is False
    mock_monitor.execute.assert_awaited_once_with(
        MonitorDeploymentStatusCommand(
            project_id=project_id,
            user_id=user_id,
            max_attempts=5,
            delay_seconds=1,
        )
    )
    mock_failure.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_monitoring_prevents_duplicate_tasks() -> None:
    # Arrange
    event = asyncio.Event()

    async def _slow_monitor(cmd: MonitorDeploymentStatusCommand) -> None:  # noqa: ARG001
        await event.wait()

    mock_monitor = AsyncMock(spec=MonitorDeploymentStatusUseCase)
    mock_monitor.execute.side_effect = _slow_monitor

    worker = DeploymentPollingWorker(monitor_use_case=mock_monitor)

    project_id = ProjectId("prj_duplicate_test")
    user_id = UserId("usr_duplicate_test")

    # Act
    task1 = worker.start_monitoring(project_id=project_id, user_id=user_id)
    task2 = worker.start_monitoring(project_id=project_id, user_id=user_id)

    # Assert - Misma tarea devuelta, no se duplica
    assert task1 is task2
    assert worker.is_monitoring(project_id) is True

    event.set()
    await task1
    assert worker.is_monitoring(project_id) is False
    assert mock_monitor.execute.await_count == 1


@pytest.mark.asyncio
async def test_start_monitoring_handles_unhandled_exception_and_triggers_failure_handler() -> None:
    # Arrange
    mock_monitor = AsyncMock(spec=MonitorDeploymentStatusUseCase)
    mock_monitor.execute.side_effect = RuntimeError("Error de red inesperado")

    mock_failure = AsyncMock(spec=HandleDeploymentFailureUseCase)

    worker = DeploymentPollingWorker(
        monitor_use_case=mock_monitor,
        failure_handler=mock_failure,
    )

    project_id = ProjectId("prj_error_test")
    user_id = UserId("usr_error_test")

    # Act
    task = worker.start_monitoring(
        project_id=project_id,
        user_id=user_id,
        provider=DeploymentProvider.RAILWAY,
    )
    await task

    # Assert
    assert worker.is_monitoring(project_id) is False
    mock_failure.execute.assert_awaited_once()
    failure_cmd = mock_failure.execute.call_args[0][0]
    assert isinstance(failure_cmd, HandleDeploymentFailureCommand)
    assert failure_cmd.project_id == project_id
    assert failure_cmd.provider == DeploymentProvider.RAILWAY
    assert "Error de red inesperado" in failure_cmd.error_message


@pytest.mark.asyncio
async def test_cancel_monitoring() -> None:
    # Arrange
    mock_monitor = AsyncMock(spec=MonitorDeploymentStatusUseCase)

    async def _infinite_monitor(cmd: MonitorDeploymentStatusCommand) -> None:  # noqa: ARG001
        while True:
            await asyncio.sleep(1)

    mock_monitor.execute.side_effect = _infinite_monitor
    worker = DeploymentPollingWorker(monitor_use_case=mock_monitor)

    project_id = ProjectId("prj_cancel_test")
    user_id = UserId("usr_cancel_test")

    # Act
    task = worker.start_monitoring(project_id=project_id, user_id=user_id)
    assert worker.is_monitoring(project_id) is True

    cancelled = worker.cancel_monitoring(project_id)
    assert cancelled is True

    with pytest.raises(asyncio.CancelledError):
        await task

    assert worker.is_monitoring(project_id) is False


@pytest.mark.asyncio
async def test_shutdown_cancels_all_active_tasks() -> None:
    # Arrange
    mock_monitor = AsyncMock(spec=MonitorDeploymentStatusUseCase)

    async def _hang_forever(cmd: MonitorDeploymentStatusCommand) -> None:  # noqa: ARG001
        while True:
            await asyncio.sleep(1)

    mock_monitor.execute.side_effect = _hang_forever
    worker = DeploymentPollingWorker(monitor_use_case=mock_monitor)

    task1 = worker.start_monitoring(project_id=ProjectId("prj_1"), user_id=UserId("usr_1"))
    task2 = worker.start_monitoring(project_id=ProjectId("prj_2"), user_id=UserId("usr_2"))

    assert worker.is_monitoring(ProjectId("prj_1")) is True
    assert worker.is_monitoring(ProjectId("prj_2")) is True

    # Act
    await worker.shutdown()

    # Assert
    assert worker.is_monitoring(ProjectId("prj_1")) is False
    assert worker.is_monitoring(ProjectId("prj_2")) is False
    assert task1.cancelled()
    assert task2.cancelled()
