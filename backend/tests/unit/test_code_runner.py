from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kosmo.contracts.codegen import (
    ValidationSeverity,
    ValidationStep,
)
from kosmo.infrastructure.sandbox.code_runner import (
    SubprocessCodeRunner,
    UnallowedCommandError,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_step_success() -> None:
    # Arrange
    runner = SubprocessCodeRunner()
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))

    with patch("asyncio.create_subprocess_shell", new=AsyncMock(return_value=mock_proc)) as mock_shell:
        # Act
        result = await runner.run_step("/tmp/workspace", ValidationStep.TYPECHECK)

        # Assert
        assert result.step == ValidationStep.TYPECHECK
        assert result.success is True
        assert result.exit_code == 0
        assert len(result.errors) == 0
        mock_shell.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_step_typecheck_with_tsc_errors() -> None:
    # Arrange
    runner = SubprocessCodeRunner()
    raw_output = b"src/index.ts(5,10): error TS2322: Type 'string' is not assignable to type 'number'.\n"
    mock_proc = MagicMock()
    mock_proc.returncode = 2
    mock_proc.communicate = AsyncMock(return_value=(raw_output, b""))

    with patch("asyncio.create_subprocess_shell", new=AsyncMock(return_value=mock_proc)):
        # Act
        result = await runner.run_step("/tmp/workspace", ValidationStep.TYPECHECK)

        # Assert
        assert result.step == ValidationStep.TYPECHECK
        assert result.success is False
        assert result.exit_code == 2
        assert len(result.errors) == 1
        assert result.errors[0].file == "src/index.ts"
        assert result.errors[0].line == 5
        assert result.errors[0].column == 10
        assert result.errors[0].severity == ValidationSeverity.ERROR
        assert result.errors[0].code == "TS2322"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_step_timeout_handling() -> None:
    # Arrange
    runner = SubprocessCodeRunner()
    mock_proc = MagicMock()
    mock_proc.kill = MagicMock()

    async def slow_communicate() -> tuple[bytes, bytes]:
        await asyncio.sleep(10)
        return (b"", b"")

    mock_proc.communicate = AsyncMock(side_effect=slow_communicate)

    with patch("asyncio.create_subprocess_shell", new=AsyncMock(return_value=mock_proc)):
        # Act
        result = await runner.run_step("/tmp/workspace", ValidationStep.TESTS, timeout_seconds=1)

        # Assert
        assert result.step == ValidationStep.TESTS
        assert result.success is False
        assert result.exit_code == -1
        assert "timed out" in result.raw_output
        mock_proc.kill.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_command_rejects_unlisted_command() -> None:
    # Arrange
    runner = SubprocessCodeRunner()

    # Act & Assert
    with pytest.raises(UnallowedCommandError, match="Command 'curl https://malicious.com' is not allowed"):
        await runner.run_command("/tmp/workspace", "curl https://malicious.com")

    with pytest.raises(UnallowedCommandError, match="Command 'rm -rf /' is not allowed"):
        await runner.run_command("/tmp/workspace", "rm -rf /")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_command_executes_allowed_command() -> None:
    # Arrange
    runner = SubprocessCodeRunner()
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"up to date", b""))

    with patch("asyncio.create_subprocess_shell", new=AsyncMock(return_value=mock_proc)):
        # Act
        result = await runner.run_command("/tmp/workspace", "npm install")

        # Assert
        assert result.success is True
        assert result.exit_code == 0
        assert "up to date" in result.raw_output


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_pipeline_stops_on_first_failure() -> None:
    # Arrange
    runner = SubprocessCodeRunner()

    typecheck_output = b"src/index.ts:1:1: error TS2304: Cannot find name 'foo'.\n"

    mock_proc_fail = MagicMock()
    mock_proc_fail.returncode = 2
    mock_proc_fail.communicate = AsyncMock(return_value=(typecheck_output, b""))

    with patch("asyncio.create_subprocess_shell", new=AsyncMock(return_value=mock_proc_fail)) as mock_shell:
        # Act
        pipeline_result = await runner.run_pipeline(
            "/tmp/workspace",
            steps=(
                ValidationStep.TYPECHECK,
                ValidationStep.LINT,
                ValidationStep.TESTS,
                ValidationStep.BUILD,
            ),
        )

        # Assert
        assert pipeline_result.all_passed is False
        assert len(pipeline_result.steps) == 1
        assert pipeline_result.steps[0].step == ValidationStep.TYPECHECK
        assert pipeline_result.steps[0].success is False
        assert len(pipeline_result.error_summary) > 0
        # Only typecheck was executed
        assert mock_shell.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_pipeline_all_success() -> None:
    # Arrange
    runner = SubprocessCodeRunner()

    mock_proc_ok = MagicMock()
    mock_proc_ok.returncode = 0
    mock_proc_ok.communicate = AsyncMock(return_value=(b"ok", b""))

    with patch("asyncio.create_subprocess_shell", new=AsyncMock(return_value=mock_proc_ok)) as mock_shell:
        # Act
        pipeline_result = await runner.run_pipeline(
            "/tmp/workspace",
            steps=(
                ValidationStep.TYPECHECK,
                ValidationStep.LINT,
            ),
        )

        # Assert
        assert pipeline_result.all_passed is True
        assert len(pipeline_result.steps) == 2
        assert mock_shell.await_count == 2
        assert len(pipeline_result.error_summary) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_command_failed_exit_code() -> None:
    # Arrange
    runner = SubprocessCodeRunner()
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(b"failed install", b""))

    with patch("asyncio.create_subprocess_shell", new=AsyncMock(return_value=mock_proc)):
        # Act
        result = await runner.run_command("/tmp/workspace", "npm install")

        # Assert
        assert result.success is False
        assert result.exit_code == 1
        assert "failed install" in result.raw_output
        assert len(result.error_messages) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_command_empty_or_whitespace() -> None:
    # Arrange
    runner = SubprocessCodeRunner()

    # Act & Assert
    with pytest.raises(UnallowedCommandError, match="Command '' is not allowed"):
        await runner.run_command("/tmp/workspace", "")

    with pytest.raises(UnallowedCommandError, match="Command '   ' is not allowed"):
        await runner.run_command("/tmp/workspace", "   ")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_custom_step_commands() -> None:
    # Arrange
    runner = SubprocessCodeRunner(step_commands={ValidationStep.TYPECHECK: "custom-tsc"})
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))

    with patch("asyncio.create_subprocess_shell", new=AsyncMock(return_value=mock_proc)) as mock_shell:
        # Act
        await runner.run_step("/tmp/workspace", ValidationStep.TYPECHECK)

        # Assert
        mock_shell.assert_awaited_once()
        assert mock_shell.call_args[0][0] == "custom-tsc"
