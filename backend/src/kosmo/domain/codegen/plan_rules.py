from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from kosmo.contracts.sdd.codegen import FileAction, ImplementationPlan
from kosmo.domain.codegen.path_safety import (
    UnsafePathError,
    sanitize_relative_path,
    validate_safe_path,
)

PROTECTED_WORKSPACE_FILES: frozenset[str] = frozenset(
    {
        "package.json",
        "tsconfig.json",
        "next.config.ts",
        "next.config.mjs",
        "next.config.js",
        "drizzle.config.ts",
        "vitest.config.ts",
        "eslint.config.mjs",
        "eslint.config.js",
        "tailwind.config.ts",
        "tailwind.config.js",
        "postcss.config.mjs",
        "postcss.config.js",
        "opencode.json",
        "AGENTS.md",
    }
)


class PlanRuleViolationType(StrEnum):
    UNSAFE_PATH = "unsafe_path"
    FILE_ALREADY_EXISTS = "file_already_exists"
    FILE_NOT_FOUND = "file_not_found"
    DUPLICATE_OPERATION = "duplicate_operation"
    EMPTY_OPERATIONS = "empty_operations"
    PROTECTED_FILE_MODIFICATION = "protected_file_modification"


@dataclass(frozen=True)
class PlanRuleViolation:
    path: str
    action: FileAction | str
    rule: PlanRuleViolationType | str
    message: str


@dataclass(frozen=True)
class PlanValidationResult:
    is_valid: bool
    violations: tuple[PlanRuleViolation, ...] = field(default_factory=tuple)
    error_summary: tuple[str, ...] = field(default_factory=tuple)


class InvalidPlanError(ValueError):
    """Lanzada cuando un ImplementationPlan no cumple con las reglas de validación."""

    def __init__(
        self,
        message: str,
        violations: tuple[PlanRuleViolation, ...] = (),
    ) -> None:
        super().__init__(message)
        self.violations = violations


def validate_plan(
    plan: ImplementationPlan,
    manifest_files: Iterable[str],
    workspace_root: str | Path = "/workspace",
) -> PlanValidationResult:
    """Valida determinísticamente las operaciones propuestas en un ImplementationPlan.

    Verifica:
    - Que el plan contenga operaciones.
    - Que cada ruta sea segura dentro del workspace_root.
    - Que CREATE no apunte a archivos ya existentes en el manifiesto.
    - Que MODIFY apunte a archivos existentes en el manifiesto.
    - Que DELETE apunte a archivos existentes y no protegidos.
    - Que no existan operaciones duplicadas sobre la misma ruta.
    """
    violations: list[PlanRuleViolation] = []

    if not plan.operations:
        violations.append(
            PlanRuleViolation(
                path="",
                action="",
                rule=PlanRuleViolationType.EMPTY_OPERATIONS,
                message="El plan de implementación no contiene operaciones de archivo.",
            )
        )
        return PlanValidationResult(
            is_valid=False,
            violations=tuple(violations),
            error_summary=("El plan de implementación no contiene operaciones de archivo.",),
        )

    # Normalizar manifiesto
    normalized_manifest: set[str] = set()
    for item in manifest_files:
        clean_item = item.strip().replace("\\", "/")
        if clean_item.startswith("./"):
            clean_item = clean_item[2:]
        elif clean_item.startswith("/"):
            clean_item = clean_item[1:]
        if clean_item:
            normalized_manifest.add(clean_item)

    seen_paths: set[str] = set()

    for op in plan.operations:
        # 1. Validar seguridad de ruta
        if not validate_safe_path(op.path, workspace_root):
            violations.append(
                PlanRuleViolation(
                    path=op.path,
                    action=op.action,
                    rule=PlanRuleViolationType.UNSAFE_PATH,
                    message=f"Ruta insegura o que intenta escapar del workspace: '{op.path}'",
                )
            )
            continue

        try:
            clean_path = sanitize_relative_path(op.path)
        except UnsafePathError as exc:
            violations.append(
                PlanRuleViolation(
                    path=op.path,
                    action=op.action,
                    rule=PlanRuleViolationType.UNSAFE_PATH,
                    message=f"Ruta inválida: {exc}",
                )
            )
            continue

        # 2. Validar duplicados
        if clean_path in seen_paths:
            violations.append(
                PlanRuleViolation(
                    path=clean_path,
                    action=op.action,
                    rule=PlanRuleViolationType.DUPLICATE_OPERATION,
                    message=f"Operación duplicada para la ruta: '{clean_path}'",
                )
            )
            continue
        seen_paths.add(clean_path)

        # 3. Validar reglas según FileAction
        if op.action == FileAction.CREATE:
            if clean_path in normalized_manifest:
                violations.append(
                    PlanRuleViolation(
                        path=clean_path,
                        action=op.action,
                        rule=PlanRuleViolationType.FILE_ALREADY_EXISTS,
                        message=f"El archivo '{clean_path}' ya existe en el workspace. Usa MODIFY en su lugar.",
                    )
                )
        elif op.action == FileAction.MODIFY:
            if clean_path not in normalized_manifest:
                violations.append(
                    PlanRuleViolation(
                        path=clean_path,
                        action=op.action,
                        rule=PlanRuleViolationType.FILE_NOT_FOUND,
                        message=f"El archivo '{clean_path}' no existe en el workspace. Usa CREATE en su lugar.",
                    )
                )
        elif op.action == FileAction.DELETE:
            if clean_path not in normalized_manifest:
                violations.append(
                    PlanRuleViolation(
                        path=clean_path,
                        action=op.action,
                        rule=PlanRuleViolationType.FILE_NOT_FOUND,
                        message=f"El archivo '{clean_path}' no existe en el workspace para ser eliminado.",
                    )
                )
            elif clean_path in PROTECTED_WORKSPACE_FILES:
                violations.append(
                    PlanRuleViolation(
                        path=clean_path,
                        action=op.action,
                        rule=PlanRuleViolationType.PROTECTED_FILE_MODIFICATION,
                        message=f"El archivo '{clean_path}' está protegido y no puede ser eliminado.",
                    )
                )

    is_valid = len(violations) == 0
    error_summary = tuple(v.message for v in violations)
    return PlanValidationResult(
        is_valid=is_valid,
        violations=tuple(violations),
        error_summary=error_summary,
    )


def ensure_valid_plan(
    plan: ImplementationPlan,
    manifest_files: Iterable[str],
    workspace_root: str | Path = "/workspace",
) -> ImplementationPlan:
    """Valida un ImplementationPlan y lo retorna si es válido; lanza InvalidPlanError si no."""
    result = validate_plan(plan, manifest_files, workspace_root)
    if not result.is_valid:
        error_detail = "; ".join(result.error_summary)
        raise InvalidPlanError(f"Plan inválido: {error_detail}", violations=result.violations)
    return plan
