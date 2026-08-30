from __future__ import annotations

import re

from kosmo.contracts.sdd.codegen import (
    ValidationErrorDetail,
    ValidationRunResult,
    ValidationSeverity,
    ValidationStep,
    ValidationStepResult,
)

_TSC_REGEX = re.compile(
    r"^(?P<file>[^(\s:]+?)(?:\((?P<line1>\d+),(?P<col1>\d+)\):?|:(?P<line2>\d+):(?P<col2>\d+):?)\s*(?:-\s*)?(?P<severity>error|warning)\s*(?P<code>TS\d+)?:\s*(?P<msg>.+)$"
)


_ESLINT_LINE_REGEX = re.compile(
    r"^\s*(?P<line>\d+):(?P<col>\d+)\s+(?P<severity>error|warning)\s+(?P<msg>.+?)(?:\s{2,}(?P<code>[@\w\-/]+))?$"
)

_ESLINT_COMPACT_REGEX = re.compile(
    r"^(?P<file>.+?):\s*line\s*(?P<line>\d+),\s*col\s*(?P<col>\d+),\s*(?P<severity>Error|Warning)\s*-\s*(?P<msg>.+?)(?:\s*\((?P<code>[@\w\-/]+)\))?$"
)

_VITEST_FAIL_REGEX = re.compile(r"^FAIL\s+(?P<file>[^\s>\[]+)")
_VITEST_LOC_REGEX = re.compile(r"^\s*❯\s+(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+)")
_VITEST_ERROR_REGEX = re.compile(r"^(?:AssertionError|Error|TypeError|ReferenceError):\s*(?P<msg>.+)$")

_NEXT_LOC_REGEX = re.compile(r"^(?:\./)?(?P<file>[^\s:]+\.(?:tsx|ts|jsx|js|css|json|mjs)):(?P<line>\d+):(?P<col>\d+)")
_NEXT_FILE_REGEX = re.compile(r"^(?:\./)?(?P<file>[^\s:]+\.(?:tsx|ts|jsx|js|css|json|mjs))\s*$")


def parse_tsc_output(raw_output: str) -> tuple[ValidationErrorDetail, ...]:
    """Parsea determinísticamente la salida de `tsc --noEmit`."""
    errors: list[ValidationErrorDetail] = []
    for line in raw_output.splitlines():
        match = _TSC_REGEX.match(line.strip())
        if match:
            file_path = match.group("file")
            line_num = int(match.group("line1") or match.group("line2") or 0)
            col_num = int(match.group("col1") or match.group("col2") or 0)
            severity_str = match.group("severity").lower()
            severity = ValidationSeverity.WARNING if severity_str == "warning" else ValidationSeverity.ERROR
            code = match.group("code")
            msg = match.group("msg").strip()

            errors.append(
                ValidationErrorDetail(
                    file=file_path,
                    line=line_num,
                    column=col_num,
                    message=msg,
                    severity=severity,
                    code=code,
                )
            )
    return tuple(errors)


def parse_eslint_output(raw_output: str) -> tuple[ValidationErrorDetail, ...]:
    """Parsea determinísticamente la salida de `eslint` en formato stylish o compact."""
    errors: list[ValidationErrorDetail] = []
    current_file: str | None = None

    for line in raw_output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Intentar formato compacto
        compact_match = _ESLINT_COMPACT_REGEX.match(stripped)
        if compact_match:
            sev_str = compact_match.group("severity").lower()
            errors.append(
                ValidationErrorDetail(
                    file=compact_match.group("file"),
                    line=int(compact_match.group("line")),
                    column=int(compact_match.group("col")),
                    message=compact_match.group("msg").strip(),
                    severity=ValidationSeverity.WARNING if sev_str == "warning" else ValidationSeverity.ERROR,
                    code=compact_match.group("code"),
                )
            )
            continue

        # Encabezado de archivo en formato stylish
        if not line.startswith(" ") and (
            stripped.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json"))
            or "/" in stripped
            or "\\" in stripped
        ):
            current_file = stripped
            continue

        # Línea de problema en formato stylish
        stylish_match = _ESLINT_LINE_REGEX.match(line)
        if stylish_match and current_file:
            sev_str = stylish_match.group("severity").lower()
            errors.append(
                ValidationErrorDetail(
                    file=current_file,
                    line=int(stylish_match.group("line")),
                    column=int(stylish_match.group("col")),
                    message=stylish_match.group("msg").strip(),
                    severity=ValidationSeverity.WARNING if sev_str == "warning" else ValidationSeverity.ERROR,
                    code=stylish_match.group("code"),
                )
            )

    return tuple(errors)


def parse_vitest_output(raw_output: str) -> tuple[ValidationErrorDetail, ...]:
    """Parsea determinísticamente la salida de `vitest run`."""
    errors: list[ValidationErrorDetail] = []
    current_file: str | None = None
    current_msg: str | None = None

    for line in raw_output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        fail_match = _VITEST_FAIL_REGEX.match(stripped)
        if fail_match:
            current_file = fail_match.group("file")
            continue

        err_match = _VITEST_ERROR_REGEX.match(stripped)
        if err_match:
            current_msg = err_match.group("msg").strip()
            continue

        loc_match = _VITEST_LOC_REGEX.match(line)
        if loc_match:
            file_path = loc_match.group("file") or current_file or "test"
            line_num = int(loc_match.group("line"))
            col_num = int(loc_match.group("col"))
            msg = current_msg or f"Test failed in {file_path}"
            errors.append(
                ValidationErrorDetail(
                    file=file_path,
                    line=line_num,
                    column=col_num,
                    message=msg,
                    severity=ValidationSeverity.ERROR,
                    code="VITEST_FAIL",
                )
            )
            current_msg = None

    return tuple(errors)


def parse_next_build_output(raw_output: str) -> tuple[ValidationErrorDetail, ...]:
    """Parsea determinísticamente la salida de `next build`."""
    errors: list[ValidationErrorDetail] = []
    lines = raw_output.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Formato ./src/app/...:line:col
        loc_match = _NEXT_LOC_REGEX.match(line)
        if loc_match:
            file_path = loc_match.group("file")
            line_num = int(loc_match.group("line"))
            col_num = int(loc_match.group("col"))
            msg = "Build compilation error"
            if i + 1 < len(lines) and lines[i + 1].strip():
                msg = lines[i + 1].strip()
                i += 1
            errors.append(
                ValidationErrorDetail(
                    file=file_path,
                    line=line_num,
                    column=col_num,
                    message=msg,
                    severity=ValidationSeverity.ERROR,
                    code="NEXT_BUILD_ERROR",
                )
            )
            i += 1
            continue

        # Formato ./src/components/Header.tsx seguido de Module not found
        file_match = _NEXT_FILE_REGEX.match(line)
        if file_match and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line.startswith("Module not found"):
                errors.append(
                    ValidationErrorDetail(
                        file=file_match.group("file"),
                        line=0,
                        column=0,
                        message=next_line,
                        severity=ValidationSeverity.ERROR,
                        code="MODULE_NOT_FOUND",
                    )
                )
                i += 2
                continue

        i += 1

    return tuple(errors)


def parse_validation_output(
    step: ValidationStep,
    raw_output: str,
) -> tuple[ValidationErrorDetail, ...]:
    """Despachador que extrae los ValidationErrorDetail según el ValidationStep."""
    if step == ValidationStep.TYPECHECK:
        return parse_tsc_output(raw_output)
    if step == ValidationStep.LINT:
        return parse_eslint_output(raw_output)
    if step == ValidationStep.TESTS:
        return parse_vitest_output(raw_output)
    if step == ValidationStep.BUILD:
        return parse_next_build_output(raw_output)
    return ()


def parse_step_output(
    step: ValidationStep,
    raw_output: str,
    exit_code: int = 0,
    duration_ms: int = 0,
) -> ValidationStepResult:
    """Construye un ValidationStepResult completo parseando la salida y determinando el éxito."""
    errors = parse_validation_output(step, raw_output)
    success = exit_code == 0 and len(errors) == 0

    if errors:
        error_messages = tuple(
            f"{e.file}:{e.line}:{e.column} [{e.code or e.severity}] {e.message}" if e.file else e.message
            for e in errors
        )
    elif not success:
        fallback = raw_output.strip() or f"Step '{step}' failed with exit code {exit_code}"
        error_messages = (fallback,)
    else:
        error_messages = ()

    return ValidationStepResult(
        step=step,
        success=success,
        duration_ms=duration_ms,
        exit_code=exit_code,
        raw_output=raw_output,
        errors=errors,
        error_messages=error_messages,
    )


def truncate_error_output(raw_output: str, max_chars: int = 6000) -> str:
    """Trunca el texto de salida respetando un límite de caracteres para presupuestos de tokens."""
    if len(raw_output) <= max_chars:
        return raw_output

    half = (max_chars - 60) // 2
    head = raw_output[:half]
    tail = raw_output[-half:]
    return f"{head}\n\n... [Output truncated for token budget] ...\n\n{tail}"


def format_validation_errors_for_prompt(
    validation_result: ValidationRunResult,
    max_chars: int = 6000,
) -> str:
    """Construye un reporte estructurado y priorizado de errores por paso para alimentar el fix prompt."""
    sections: list[str] = []
    for step_res in validation_result.steps:
        if step_res.success:
            continue

        step_name = step_res.step.value if hasattr(step_res.step, "value") else str(step_res.step)
        step_header = f"### Fallo en paso: {step_name.upper()}"

        if step_res.error_messages:
            msgs = "\n".join(f"- {msg}" for msg in step_res.error_messages)
            sections.append(f"{step_header}\n{msgs}")
        elif step_res.raw_output:
            truncated = truncate_error_output(step_res.raw_output.strip(), max_chars=2000)
            sections.append(f"{step_header}\n```\n{truncated}\n```")
        else:
            sections.append(f"{step_header}\n- Falló con código de salida {step_res.exit_code}")

    combined = "\n\n".join(sections)
    if not combined and validation_result.error_summary:
        combined = "\n".join(f"- {s}" for s in validation_result.error_summary)

    return truncate_error_output(combined, max_chars=max_chars)


def derive_fix_directives(validation_result: ValidationRunResult) -> tuple[str, ...]:
    """Genera directivas de corrección específicas y accionables según las categorías de fallos detectados."""
    directives: list[str] = []
    failed_steps = {s.step for s in validation_result.steps if not s.success}

    if ValidationStep.STRUCTURE in failed_steps:
        directives.append(
            "Estructura: Asegúrate de crear `src/app/<slug>/page.tsx`, la carpeta `src/features/<slug>/` "
            "y registrar el manifest de la funcionalidad en `src/lib/feature-registry.ts`."
        )

    has_import_error = False
    for step_res in validation_result.steps:
        if not step_res.success:
            for err in step_res.errors:
                code_str = (err.code or "").upper()
                msg_str = (err.message or "").lower()
                if "module_not_found" in code_str or "ts2307" in code_str or "cannot find module" in msg_str:
                    has_import_error = True
                    break
            if not has_import_error and any(
                "cannot find module" in m.lower() or "module not found" in m.lower() for m in step_res.error_messages
            ):
                has_import_error = True

    if has_import_error:
        directives.append(
            "Importaciones: Corrige las rutas de importación relativas o alias `@/` y "
            "verifica que los archivos exporten los símbolos requeridos."
        )

    if ValidationStep.TYPECHECK in failed_steps and not has_import_error:
        directives.append(
            "Tipado TypeScript: Corrige las firmas de funciones, parámetros y tipos de retorno "
            "para cumplir estrictamente con los contratos declarados."
        )

    if ValidationStep.TESTS in failed_steps:
        directives.append(
            "Lógica y pruebas: Ajusta la lógica de negocio en `src/features/<slug>/logic.ts` para "
            "satisfacer los criterios y aserciones de Vitest según los requisitos EARS. "
            "No elimines ni desactives pruebas válidas."
        )

    if ValidationStep.LINT in failed_steps:
        directives.append("Linter: Limpia imports no utilizados y corrige errores de formato de ESLint.")

    has_db_error = any(
        "src/db" in (err.file or "").lower() or "drizzle" in (err.file or "").lower()
        for step_res in validation_result.steps
        if not step_res.success
        for err in step_res.errors
    ) or any(
        "src/db" in msg.lower() or "drizzle" in msg.lower()
        for step_res in validation_result.steps
        if not step_res.success
        for msg in step_res.error_messages
    )

    if has_db_error:
        directives.append(
            "Base de datos / Drizzle: Verifica las definiciones de tablas en `src/db/schema.ts` usando "
            "`sqliteTable`, `text`, `integer`, `real` de `drizzle-orm/sqlite-core` y consultas tipadas con `db`."
        )

    if ValidationStep.BUILD in failed_steps:
        directives.append(
            "Compilación Next.js: Asegúrate de agregar `'use client'` al inicio de los componentes con "
            "interactividad o hooks de React (useState, useEffect, onClick) y verificar el empaquetado."
        )

    if not directives:
        directives.append("Corrige los archivos necesarios en el workspace para resolver los errores detectados.")

    return tuple(directives)
