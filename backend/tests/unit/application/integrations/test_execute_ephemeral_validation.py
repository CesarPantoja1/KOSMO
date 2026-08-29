from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from kosmo.application.integrations.execute_ephemeral_validation import (
    ExecuteEphemeralValidationCommand,
    ExecuteEphemeralValidationUseCase,
)
from kosmo.contracts.sdd.codegen import (
    CodeRunnerPort,
    CodeWorkspace,
    ValidationErrorDetail,
    ValidationSeverity,
    ValidationStep,
    ValidationStepResult,
    WorkspaceManagerPort,
)
from kosmo.contracts.sdd.ids import ProjectId, WorkspaceId


@pytest.fixture
def code_runner() -> AsyncMock:
    return AsyncMock(spec=CodeRunnerPort)


@pytest.fixture
def workspace_manager() -> AsyncMock:
    return AsyncMock(spec=WorkspaceManagerPort)


@pytest.fixture
def use_case(
    code_runner: AsyncMock,
    workspace_manager: AsyncMock,
) -> ExecuteEphemeralValidationUseCase:
    return ExecuteEphemeralValidationUseCase(
        code_runner=code_runner,
        workspace_manager=workspace_manager,
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_ephemeral_validation_success_all_steps_pass(
    use_case: ExecuteEphemeralValidationUseCase,
    code_runner: AsyncMock,
) -> None:
    # Arrange
    workspace_path = "/tmp/workspaces/proj-valid"
    code_runner.run_step.side_effect = [
        ValidationStepResult(step=ValidationStep.TYPECHECK, success=True, duration_ms=100),
        ValidationStepResult(step=ValidationStep.LINT, success=True, duration_ms=80),
        ValidationStepResult(step=ValidationStep.TESTS, success=True, duration_ms=250),
        ValidationStepResult(step=ValidationStep.BUILD, success=True, duration_ms=400),
    ]

    cmd = ExecuteEphemeralValidationCommand(workspace_path=workspace_path)

    # Act
    result = await use_case.execute(cmd)

    # Assert
    assert result.is_valid is True
    assert len(result.steps) == 4
    assert result.failed_step is None
    assert len(result.error_summary) == 0
    assert result.total_duration_ms == 830
    assert result.run_result.all_passed is True

    # Verificar que se invocaron los pasos en orden
    assert code_runner.run_step.call_count == 4
    calls = [call[1]["step"] for call in code_runner.run_step.call_args_list]
    assert calls == [
        ValidationStep.TYPECHECK,
        ValidationStep.LINT,
        ValidationStep.TESTS,
        ValidationStep.BUILD,
    ]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_ephemeral_validation_fails_on_broken_step(
    use_case: ExecuteEphemeralValidationUseCase,
    code_runner: AsyncMock,
) -> None:
    # Arrange
    workspace_path = "/tmp/workspaces/proj-broken"
    error_detail = ValidationErrorDetail(
        file="src/index.ts",
        line=12,
        column=5,
        message="Type 'string' is not assignable to type 'number'.",
        severity=ValidationSeverity.ERROR,
    )
    code_runner.run_step.side_effect = [
        ValidationStepResult(
            step=ValidationStep.TYPECHECK,
            success=False,
            duration_ms=120,
            exit_code=1,
            errors=(error_detail,),
            error_messages=("Type error in src/index.ts",),
        ),
    ]

    cmd = ExecuteEphemeralValidationCommand(workspace_path=workspace_path)

    # Act
    result = await use_case.execute(cmd)

    # Assert
    assert result.is_valid is False
    assert result.failed_step == ValidationStep.TYPECHECK
    assert len(result.steps) == 1
    assert "Type error in src/index.ts" in result.error_summary
    assert result.run_result.all_passed is False

    # Early termination: no se ejecutaron los siguientes pasos tras el fallo
    assert code_runner.run_step.call_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_ephemeral_validation_resolves_workspace_from_project_id(
    use_case: ExecuteEphemeralValidationUseCase,
    code_runner: AsyncMock,
    workspace_manager: AsyncMock,
) -> None:
    # Arrange
    project_id = ProjectId("proj-resolver")
    workspace_manager.get_workspace.return_value = CodeWorkspace(
        id=WorkspaceId("ws-1"),
        project_id=project_id,
        workspace_dir="/tmp/resolved/workspace/path",
    )
    code_runner.run_step.return_value = ValidationStepResult(
        step=ValidationStep.TYPECHECK,
        success=True,
        duration_ms=50,
    )

    cmd = ExecuteEphemeralValidationCommand(
        project_id=project_id,
        steps=(ValidationStep.TYPECHECK,),
    )

    # Act
    result = await use_case.execute(cmd)

    # Assert
    assert result.is_valid is True
    workspace_manager.get_workspace.assert_called_once_with(project_id)
    code_runner.run_step.assert_called_once_with(
        workspace_dir="/tmp/resolved/workspace/path",
        step=ValidationStep.TYPECHECK,
        timeout_seconds=300,
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_ephemeral_validation_raises_when_workspace_not_found(
    use_case: ExecuteEphemeralValidationUseCase,
    workspace_manager: AsyncMock,
) -> None:
    # Arrange
    project_id = ProjectId("proj-missing")
    workspace_manager.get_workspace.return_value = None

    cmd = ExecuteEphemeralValidationCommand(project_id=project_id)

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        await use_case.execute(cmd)

    assert "directorio físico del workspace" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_ephemeral_validation_raises_when_no_path_nor_project_id(
    use_case: ExecuteEphemeralValidationUseCase,
) -> None:
    # Arrange
    cmd = ExecuteEphemeralValidationCommand()

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        await use_case.execute(cmd)

    assert "Se requiere 'workspace_path' o 'project_id'" in str(exc_info.value)
