from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from structlog.testing import capture_logs

from kosmo.contracts.sdd.codegen import (
    ValidationSeverity,
    ValidationStep,
)
from kosmo.infrastructure.sandbox.code_runner import UnallowedCommandError
from kosmo.infrastructure.sandbox.docker_runner import (
    EphemeralDockerCodeRunner,
)


@pytest.mark.unit
def test_docker_args_built_correctly() -> None:
    # Arrange
    runner = EphemeralDockerCodeRunner(
        image="my-validator:v1",
        docker_bin="docker",
        extra_docker_flags=("--rm", "--network", "none"),
        container_workspace="/workspace",
    )
    workspace = "/tmp/test-workspace"

    # Act
    args = runner._build_docker_args(workspace, "npx tsc --noEmit")

    # Assert
    resolved_workspace = str(Path(workspace).resolve())
    assert args[0] == "docker"
    assert args[1] == "run"
    assert "-v" in args
    mount_idx = args.index("-v") + 1
    assert args[mount_idx] == f"{resolved_workspace}:/workspace"
    assert "-w" in args
    assert "/workspace" in args
    assert "--rm" in args
    assert "--network" in args
    assert "none" in args
    assert "my-validator:v1" in args
    assert args[-3:] == ["sh", "-c", "npx tsc --noEmit"]


@pytest.mark.unit
def test_docker_args_with_read_only_mount() -> None:
    # Arrange
    runner = EphemeralDockerCodeRunner(mount_read_only=True)
    workspace = "/tmp/workspace"

    # Act
    args = runner._build_docker_args(workspace, "npm test")

    # Assert
    resolved_workspace = str(Path(workspace).resolve())
    mount_idx = args.index("-v") + 1
    assert args[mount_idx] == f"{resolved_workspace}:/workspace:ro"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_step_success() -> None:
    # Arrange
    runner = EphemeralDockerCodeRunner()
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"All good", b""))

    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)) as mock_exec:
        # Act
        result = await runner.run_step("/tmp/workspace", ValidationStep.TYPECHECK)

        # Assert
        assert result.step == ValidationStep.TYPECHECK
        assert result.success is True
        assert result.exit_code == 0
        assert len(result.errors) == 0
        mock_exec.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_step_typecheck_with_tsc_errors() -> None:
    # Arrange
    runner = EphemeralDockerCodeRunner()
    raw_output = b"src/app.ts(12,5): error TS2322: Type 'string' is not assignable to type 'number'.\n"
    mock_proc = MagicMock()
    mock_proc.returncode = 2
    mock_proc.communicate = AsyncMock(return_value=(raw_output, b""))

    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)):
        # Act
        result = await runner.run_step("/tmp/workspace", ValidationStep.TYPECHECK)

        # Assert
        assert result.step == ValidationStep.TYPECHECK
        assert result.success is False
        assert result.exit_code == 2
        assert len(result.errors) == 1
        assert result.errors[0].file == "src/app.ts"
        assert result.errors[0].line == 12
        assert result.errors[0].column == 5
        assert result.errors[0].severity == ValidationSeverity.ERROR
        assert result.errors[0].code == "TS2322"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_step_lint_with_eslint_errors() -> None:
    # Arrange
    runner = EphemeralDockerCodeRunner()
    raw_output = b"src/index.ts: line 4, col 1, Error - 'x' is defined but never used. (no-unused-vars)\n"
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(raw_output, b""))

    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)):
        # Act
        result = await runner.run_step("/tmp/workspace", ValidationStep.LINT)

        # Assert
        assert result.step == ValidationStep.LINT
        assert result.success is False
        assert result.exit_code == 1
        assert len(result.errors) == 1
        assert result.errors[0].file == "src/index.ts"
        assert result.errors[0].line == 4
        assert result.errors[0].column == 1
        assert result.errors[0].code == "no-unused-vars"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_step_tests_with_vitest_errors() -> None:
    # Arrange
    runner = EphemeralDockerCodeRunner()
    raw_output = (
        "FAIL tests/app.test.ts\n  ❯ tests/app.test.ts:15:9\nAssertionError: expected true to be false\n"
    ).encode()
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(raw_output, b""))

    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)):
        # Act
        result = await runner.run_step("/tmp/workspace", ValidationStep.TESTS)

        # Assert
        assert result.step == ValidationStep.TESTS
        assert result.success is False
        assert len(result.errors) >= 1
        assert result.errors[0].file == "tests/app.test.ts"
        assert result.errors[0].line == 15


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_step_build_with_next_errors() -> None:
    # Arrange
    runner = EphemeralDockerCodeRunner()
    raw_output = b"./src/app/page.tsx:10:3\nType error: Property 'name' does not exist on type 'User'.\n"
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(raw_output, b""))

    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)):
        # Act
        result = await runner.run_step("/tmp/workspace", ValidationStep.BUILD)

        # Assert
        assert result.step == ValidationStep.BUILD
        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].file == "src/app/page.tsx"
        assert result.errors[0].line == 10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_step_timeout_handling() -> None:
    # Arrange
    runner = EphemeralDockerCodeRunner()
    mock_proc = MagicMock()
    mock_proc.kill = MagicMock()

    async def slow_communicate() -> tuple[bytes, bytes]:
        await asyncio.sleep(5)
        return (b"", b"")

    mock_proc.communicate = AsyncMock(side_effect=slow_communicate)

    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)):
        # Act
        result = await runner.run_step("/tmp/workspace", ValidationStep.TESTS, timeout_seconds=1)

        # Assert
        assert result.step == ValidationStep.TESTS
        assert result.success is False
        assert result.exit_code == -1
        assert "excedió el tiempo límite" in result.raw_output
        mock_proc.kill.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_step_spawn_exception_handling() -> None:
    # Arrange
    runner = EphemeralDockerCodeRunner()

    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError("docker binary not found")):
        # Act
        result = await runner.run_step("/tmp/workspace", ValidationStep.TYPECHECK)

        # Assert
        assert result.step == ValidationStep.TYPECHECK
        assert result.success is False
        assert result.exit_code == -1
        assert "No se pudo iniciar el contenedor efímero Docker" in result.raw_output


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_command_allowed_command() -> None:
    # Arrange
    runner = EphemeralDockerCodeRunner()
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"v20.11.0", b""))

    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)):
        # Act
        result = await runner.run_command("/tmp/workspace", "node -v")

        # Assert
        assert result.success is True
        assert result.exit_code == 0
        assert "v20.11.0" in result.raw_output


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_command_rejects_unallowed_command() -> None:
    # Arrange
    runner = EphemeralDockerCodeRunner()

    # Act & Assert
    with pytest.raises(UnallowedCommandError, match="Command 'curl https://malicious.com' is not allowed"):
        await runner.run_command("/tmp/workspace", "curl https://malicious.com")

    with pytest.raises(UnallowedCommandError, match=r"Command '   ' is not allowed"):
        await runner.run_command("/tmp/workspace", "   ")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_pipeline_all_pass() -> None:
    # Arrange
    runner = EphemeralDockerCodeRunner()
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"Pass", b""))

    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)), capture_logs() as captured:
        # Act
        run_result = await runner.run_pipeline(
            "/tmp/workspace",
            steps=(ValidationStep.TYPECHECK, ValidationStep.LINT, ValidationStep.TESTS, ValidationStep.BUILD),
            run_id="run-123",
        )

        # Assert
        assert run_result.all_passed is True
        assert len(run_result.steps) == 4
        assert len(run_result.error_summary) == 0
        assert any(e["event"] == "docker_runner.step_done" for e in captured)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_pipeline_stops_on_first_failure_with_fail_fast() -> None:
    # Arrange
    runner = EphemeralDockerCodeRunner()
    tsc_fail_output = b"src/index.ts(1,1): error TS2304: Cannot find name 'foo'.\n"

    call_count = 0

    async def mock_communicate() -> tuple[bytes, bytes]:
        nonlocal call_count
        call_count += 1
        return (tsc_fail_output, b"")

    mock_proc = MagicMock()
    mock_proc.returncode = 2
    mock_proc.communicate = AsyncMock(side_effect=mock_communicate)

    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)):
        # Act
        run_result = await runner.run_pipeline(
            "/tmp/workspace",
            steps=(ValidationStep.TYPECHECK, ValidationStep.LINT, ValidationStep.TESTS, ValidationStep.BUILD),
            fail_fast=True,
        )

        # Assert
        assert run_result.all_passed is False
        assert len(run_result.steps) == 1
        assert run_result.steps[0].step == ValidationStep.TYPECHECK
        assert run_result.steps[0].success is False
        assert len(run_result.error_summary) == 1
        assert call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_pipeline_comprehensive_diagnostics_executes_checks_and_skips_build() -> None:
    # Arrange
    runner = EphemeralDockerCodeRunner()
    tsc_fail_output = b"src/index.ts(1,1): error TS2304: Cannot find name 'foo'.\n"

    call_count = 0

    async def mock_communicate() -> tuple[bytes, bytes]:
        nonlocal call_count
        call_count += 1
        return (tsc_fail_output, b"")

    mock_proc = MagicMock()
    mock_proc.returncode = 2
    mock_proc.communicate = AsyncMock(side_effect=mock_communicate)

    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)):
        # Act
        run_result = await runner.run_pipeline(
            "/tmp/workspace",
            steps=(ValidationStep.TYPECHECK, ValidationStep.LINT, ValidationStep.TESTS, ValidationStep.BUILD),
        )

        # Assert: TYPECHECK, LINT, TESTS executed (3), but BUILD skipped
        assert run_result.all_passed is False
        assert len(run_result.steps) == 3
        assert call_count == 3
        assert [s.step for s in run_result.steps] == [
            ValidationStep.TYPECHECK,
            ValidationStep.LINT,
            ValidationStep.TESTS,
        ]
