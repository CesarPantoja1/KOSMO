from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from kosmo.contracts.sdd.codegen import (
    CodeRunnerPort,
    ValidationRunResult,
    ValidationStep,
    ValidationStepResult,
    WorkspaceManagerPort,
)
from kosmo.contracts.sdd.ids import ProjectId

DEFAULT_EPHEMERAL_VALIDATION_STEPS: tuple[ValidationStep, ...] = (
    ValidationStep.TYPECHECK,
    ValidationStep.LINT,
    ValidationStep.TESTS,
    ValidationStep.BUILD,
)


class EphemeralValidationError(RuntimeError):
    """Lanzada cuando la validación en contenedor efímero detecta errores en el workspace."""

    def __init__(
        self,
        message: str,
        step: ValidationStep | None = None,
        errors: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.step = step
        self.errors = errors


@dataclass(frozen=True, slots=True)
class ExecuteEphemeralValidationCommand:
    workspace_path: str | None = None
    project_id: ProjectId | None = None
    steps: tuple[ValidationStep, ...] = DEFAULT_EPHEMERAL_VALIDATION_STEPS
    timeout_seconds: int = 300


@dataclass(frozen=True, slots=True)
class ExecuteEphemeralValidationResult:
    is_valid: bool
    steps: tuple[ValidationStepResult, ...]
    failed_step: ValidationStep | None = None
    error_summary: tuple[str, ...] = field(default_factory=tuple)
    total_duration_ms: int = 0
    run_result: ValidationRunResult = field(default_factory=lambda: ValidationRunResult())


class ExecuteEphemeralValidationUseCase:
    """Caso de uso para ejecutar validación determinística en un contenedor efímero aislado (C7).

    Orquesta la verificación secuencial de compilación, análisis estático y pruebas del código
    generado dentro de un entorno aislado, asegurando que el espacio de trabajo local permanezca
    limpio y verificado antes de sincronizar con el repositorio remoto.
    """

    def __init__(
        self,
        code_runner: CodeRunnerPort,
        workspace_manager: WorkspaceManagerPort | None = None,
    ) -> None:
        self._code_runner = code_runner
        self._workspace_manager = workspace_manager

    async def execute(
        self,
        cmd: ExecuteEphemeralValidationCommand,
    ) -> ExecuteEphemeralValidationResult:
        # 1. Determinar el directorio físico del workspace
        workspace_dir = cmd.workspace_path

        if not workspace_dir and cmd.project_id is not None:
            if self._workspace_manager is None:
                raise ValueError("No se proporcionó WorkspaceManagerPort para resolver el project_id.")
            workspace = await self._workspace_manager.ensure_workspace(cmd.project_id)
            if not workspace or not workspace.workspace_dir:
                raise ValueError(
                    f"No se encontró el directorio físico del workspace para el proyecto '{cmd.project_id}'."
                )
            workspace_dir = workspace.workspace_dir

        if not workspace_dir:
            raise ValueError("Se requiere 'workspace_path' o 'project_id' válido para ejecutar la validación efímera.")

        # 2. Ejecutar secuencialmente los pasos en el contenedor efímero
        step_results: list[ValidationStepResult] = []
        all_passed = True
        failed_step: ValidationStep | None = None
        error_summary_list: list[str] = []
        total_duration_ms = 0

        for step in cmd.steps:
            res = await self._code_runner.run_step(
                workspace_dir=workspace_dir,
                step=step,
                timeout_seconds=cmd.timeout_seconds,
            )
            step_results.append(res)
            total_duration_ms += res.duration_ms

            if not res.success:
                all_passed = False
                failed_step = step
                for msg in res.error_messages:
                    error_summary_list.append(msg)
                if not res.error_messages and res.errors:
                    for err in res.errors:
                        error_summary_list.append(f"{err.file}:{err.line}:{err.column}: {err.message}")
                if not error_summary_list:
                    error_summary_list.append(f"El paso '{step}' falló con código de salida {res.exit_code}.")
                # Detener tempranamente en el primer fallo
                break

        run_result = ValidationRunResult(
            steps=tuple(step_results),
            all_passed=all_passed,
            total_duration_ms=total_duration_ms,
            executed_at=datetime.now(UTC),
            error_summary=tuple(error_summary_list),
        )

        return ExecuteEphemeralValidationResult(
            is_valid=all_passed,
            steps=tuple(step_results),
            failed_step=failed_step,
            error_summary=tuple(error_summary_list),
            total_duration_ms=total_duration_ms,
            run_result=run_result,
        )
