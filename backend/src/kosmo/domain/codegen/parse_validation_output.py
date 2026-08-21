from __future__ import annotations

import re

from kosmo.contracts.codegen import (
    ValidationErrorDetail,
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


def truncate_error_output(raw_output: str, max_chars: int = 4000) -> str:
    """Trunca el texto de salida respetando un límite de caracteres para presupuestos de tokens."""
    if len(raw_output) <= max_chars:
        return raw_output

    half = (max_chars - 60) // 2
    head = raw_output[:half]
    tail = raw_output[-half:]
    return f"{head}\n\n... [Output truncated for token budget] ...\n\n{tail}"
