from __future__ import annotations

import asyncio
import contextlib
import os
import shlex
import time
from datetime import UTC, datetime
from pathlib import Path

import structlog

from kosmo.contracts.sdd.codegen import (
    CodeRunnerPort,
    ValidationRunResult,
    ValidationStep,
    ValidationStepResult,
)
from kosmo.domain.codegen.parse_validation_output import parse_step_output

_log = structlog.get_logger("kosmo.sandbox.code_runner")

DEFAULT_STEP_COMMANDS: dict[ValidationStep, str] = {
    ValidationStep.TYPECHECK: "npx tsc --noEmit",
    ValidationStep.LINT: "npx eslint .",
    ValidationStep.TESTS: "npx vitest run",
    ValidationStep.BUILD: "npx next build",
}

INSTALL_COMMAND: str = "npm install"
INSTALL_TIMEOUT_SECONDS: int = 600

DEFAULT_ALLOWED_COMMAND_PREFIXES: frozenset[str] = frozenset(
    {
        "npm",
        "npx",
        "tsc",
        "eslint",
        "vitest",
        "next",
        "git",
        "drizzle-kit",
        "node",
        "pnpm",
        "yarn",
        "pytest",
        "python",
        "pyright",
        "ruff",
    }
)

SENSITIVE_ENV_VARS: frozenset[str] = frozenset(
    {
        "DATABASE_URL",
        "KOSMO_SECRET_KEY",
        "JWT_SECRET",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "SECRET_KEY",
    }
)


class UnallowedCommandError(ValueError):
    """Lanzada cuando un comando no está en la lista de permitidos."""


class SubprocessCodeRunner(CodeRunnerPort):
    """Adaptador de infraestructura que ejecuta validaciones determinísticas en subprocesos."""

    def __init__(
        self,
        step_commands: dict[ValidationStep, str] | None = None,
        allowed_prefixes: frozenset[str] = DEFAULT_ALLOWED_COMMAND_PREFIXES,
    ) -> None:
        self._step_commands = dict(DEFAULT_STEP_COMMANDS)
        if step_commands:
            self._step_commands.update(step_commands)
        self._allowed_prefixes = allowed_prefixes

    @staticmethod
    def _clean_env() -> dict[str, str]:
        return {k: v for k, v in os.environ.items() if k not in SENSITIVE_ENV_VARS}

    def _is_command_allowed(self, command: str) -> bool:
        stripped = command.strip()
        if not stripped:
            return False

        try:
            tokens = shlex.split(stripped, posix=os.name != "nt")
        except ValueError:
            tokens = stripped.split()

        if not tokens:
            return False

        first_token = tokens[0].lower()
        base_name = Path(first_token).stem.lower()

        return base_name in self._allowed_prefixes or first_token in self._allowed_prefixes

    async def _execute_command(
        self,
        workspace_dir: str,
        command: str,
        step: ValidationStep | None,
        timeout_seconds: int,
    ) -> ValidationStepResult:
        start = time.perf_counter()

        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=workspace_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=self._clean_env(),
        )

        try:
            stdout, _ = await asyncio.wait_for(
                proc.communicate(),
                timeout=float(timeout_seconds),
            )
        except TimeoutError:
            with contextlib.suppress(Exception):
                proc.kill()

            duration_ms = int((time.perf_counter() - start) * 1000)
            timeout_msg = f"Command '{command}' timed out after {timeout_seconds} seconds."
            return ValidationStepResult(
                step=step or ValidationStep.TESTS,
                success=False,
                duration_ms=duration_ms,
                exit_code=-1,
                raw_output=timeout_msg,
                errors=(),
                error_messages=(timeout_msg,),
            )

        duration_ms = int((time.perf_counter() - start) * 1000)
        raw_output = stdout.decode("utf-8", errors="replace")
        exit_code = proc.returncode if proc.returncode is not None else 0

        if step is not None:
            return parse_step_output(
                step=step,
                raw_output=raw_output,
                exit_code=exit_code,
                duration_ms=duration_ms,
            )

        success = exit_code == 0
        error_msgs = () if success else (f"Command failed with exit code {exit_code}",)
        return ValidationStepResult(
            step=ValidationStep.TESTS,
            success=success,
            duration_ms=duration_ms,
            exit_code=exit_code,
            raw_output=raw_output,
            errors=(),
            error_messages=error_msgs,
        )

    async def run_step(
        self,
        workspace_dir: str,
        step: ValidationStep,
        *,
        timeout_seconds: int = 300,
    ) -> ValidationStepResult:
        """Ejecuta el paso de validación y parsea su salida determinísticamente."""
        command = self._step_commands[step]
        return await self._execute_command(
            workspace_dir=workspace_dir,
            command=command,
            step=step,
            timeout_seconds=timeout_seconds,
        )

    async def run_command(
        self,
        workspace_dir: str,
        command: str,
        *,
        timeout_seconds: int = 300,
    ) -> ValidationStepResult:
        """Ejecuta un comando validando previamente que pertenezca a la whitelist."""
        if not self._is_command_allowed(command):
            raise UnallowedCommandError(f"Command '{command}' is not allowed.")

        return await self._execute_command(
            workspace_dir=workspace_dir,
            command=command,
            step=None,
            timeout_seconds=timeout_seconds,
        )

    async def run_pipeline(
        self,
        workspace_dir: str,
        steps: tuple[ValidationStep, ...] = (
            ValidationStep.TYPECHECK,
            ValidationStep.LINT,
            ValidationStep.TESTS,
            ValidationStep.BUILD,
        ),
        run_id: str = "",
    ) -> ValidationRunResult:
        """Ejecuta secuencialmente los pasos deteniéndose en el primer fallo (gate secuencial)."""
        if not (Path(workspace_dir) / "node_modules").is_dir():
            install_result = await self.run_command(
                workspace_dir,
                INSTALL_COMMAND,
                timeout_seconds=INSTALL_TIMEOUT_SECONDS,
            )
            if not install_result.success:
                _log.warning(
                    "code_runner.install_failed",
                    run_id=run_id,
                    workspace_dir=workspace_dir,
                    exit_code=install_result.exit_code,
                )
                output_lines = install_result.raw_output.strip().splitlines()
                detail = output_lines[0] if output_lines else "sin salida"
                return ValidationRunResult(
                    steps=(),
                    all_passed=False,
                    total_duration_ms=install_result.duration_ms,
                    executed_at=datetime.now(UTC),
                    error_summary=(f"{INSTALL_COMMAND} falló (exit {install_result.exit_code}): {detail}",),
                )

        results: list[ValidationStepResult] = []

        for step in steps:
            result = await self.run_step(workspace_dir, step)
            _log.info(
                "code_runner.step_done",
                run_id=run_id,
                workspace_dir=workspace_dir,
                step=str(step),
                success=result.success,
                duration_ms=result.duration_ms,
            )
            results.append(result)
            if not result.success:
                break

        all_passed = len(results) == len(steps) and all(r.success for r in results)
        total_duration = sum(r.duration_ms for r in results)
        error_summary = tuple(err for r in results for err in r.error_messages)

        return ValidationRunResult(
            steps=tuple(results),
            all_passed=all_passed,
            total_duration_ms=total_duration,
            executed_at=datetime.now(UTC),
            error_summary=error_summary,
        )
