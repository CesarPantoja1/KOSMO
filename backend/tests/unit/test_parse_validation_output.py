from __future__ import annotations

import pytest

from kosmo.contracts.sdd.codegen import (
    ValidationErrorDetail,
    ValidationRunResult,
    ValidationSeverity,
    ValidationStep,
    ValidationStepResult,
)
from kosmo.domain.codegen.parse_validation_output import (
    format_validation_errors_for_prompt,
    parse_eslint_output,
    parse_next_build_output,
    parse_step_output,
    parse_tsc_output,
    parse_validation_output,
    parse_vitest_output,
    truncate_error_output,
)


@pytest.mark.unit
def test_parse_tsc_output_extracts_errors_and_warnings() -> None:
    # Arrange
    raw_tsc = """
src/index.ts:12:5 - error TS2322: Type 'string' is not assignable to type 'number'.
src/components/Button.tsx(45,3): error TS2304: Cannot find name 'iconName'.
src/app/page.tsx:8:10 - warning TS7006: Parameter 'e' implicitly has an 'any' type.

Found 2 errors and 1 warning in 3 files.
"""

    # Act
    errors: tuple[ValidationErrorDetail, ...] = parse_tsc_output(raw_tsc)

    # Assert
    assert len(errors) == 3
    # Error 1
    assert errors[0].file == "src/index.ts"
    assert errors[0].line == 12
    assert errors[0].column == 5
    assert errors[0].severity == ValidationSeverity.ERROR
    assert errors[0].code == "TS2322"
    assert "Type 'string' is not assignable" in errors[0].message

    # Error 2
    assert errors[1].file == "src/components/Button.tsx"
    assert errors[1].line == 45
    assert errors[1].column == 3
    assert errors[1].severity == ValidationSeverity.ERROR
    assert errors[1].code == "TS2304"
    assert "Cannot find name 'iconName'" in errors[1].message

    # Warning 3
    assert errors[2].file == "src/app/page.tsx"
    assert errors[2].line == 8
    assert errors[2].column == 10
    assert errors[2].severity == ValidationSeverity.WARNING
    assert errors[2].code == "TS7006"


@pytest.mark.unit
def test_parse_tsc_output_returns_empty_on_clean_output() -> None:
    # Arrange
    clean_tsc = ""

    # Act
    errors = parse_tsc_output(clean_tsc)

    # Assert
    assert errors == ()


@pytest.mark.unit
def test_parse_eslint_output_extracts_stylish_errors() -> None:
    # Arrange
    raw_eslint = """
/workspaces/prj_01/src/index.ts
  12:5   error    'foo' is defined but never used  @typescript-eslint/no-unused-vars
  24:1   warning  Unexpected console statement     no-console

/workspaces/prj_01/src/lib/calc.ts
  10:15  error    Expected '===' and instead saw '=='  eqeqeq

✖ 3 problems (2 errors, 1 warning)
"""

    # Act
    errors = parse_eslint_output(raw_eslint)

    # Assert
    assert len(errors) == 3
    assert errors[0].file == "/workspaces/prj_01/src/index.ts"
    assert errors[0].line == 12
    assert errors[0].column == 5
    assert errors[0].severity == ValidationSeverity.ERROR
    assert errors[0].code == "@typescript-eslint/no-unused-vars"
    assert "'foo' is defined but never used" in errors[0].message

    assert errors[1].file == "/workspaces/prj_01/src/index.ts"
    assert errors[1].line == 24
    assert errors[1].column == 1
    assert errors[1].severity == ValidationSeverity.WARNING
    assert errors[1].code == "no-console"

    assert errors[2].file == "/workspaces/prj_01/src/lib/calc.ts"
    assert errors[2].line == 10
    assert errors[2].column == 15
    assert errors[2].severity == ValidationSeverity.ERROR
    assert errors[2].code == "eqeqeq"


@pytest.mark.unit
def test_parse_eslint_output_compact_format() -> None:
    # Arrange
    raw_eslint = (
        "src/index.ts: line 12, col 5, Error - 'foo' is defined but never used (@typescript-eslint/no-unused-vars)"
    )

    # Act
    errors = parse_eslint_output(raw_eslint)

    # Assert
    assert len(errors) == 1
    assert errors[0].file == "src/index.ts"
    assert errors[0].line == 12
    assert errors[0].column == 5
    assert errors[0].severity == ValidationSeverity.ERROR
    assert errors[0].code == "@typescript-eslint/no-unused-vars"


@pytest.mark.unit
def test_parse_vitest_output_extracts_test_failures() -> None:
    # Arrange
    raw_vitest = """
FAIL tests/expenses.test.ts > calculate expenses > should split equally
AssertionError: expected 30 to be 33.33
 ❯ tests/expenses.test.ts:24:12
     22|   const result = calculateSplit(100, 3);
     23|   expect(result[0]).toBe(30);
     24|   expect(result[1]).toBe(33.33);

FAIL tests/auth.test.ts > login flow > should reject invalid password
Error: User not found in database
 ❯ tests/auth.test.ts:50:5

Test Files  2 failed | 3 passed (5)
Tests  2 failed | 12 passed (14)
"""

    # Act
    errors = parse_vitest_output(raw_vitest)

    # Assert
    assert len(errors) == 2
    assert errors[0].file == "tests/expenses.test.ts"
    assert errors[0].line == 24
    assert errors[0].column == 12
    assert errors[0].severity == ValidationSeverity.ERROR
    assert "expected 30 to be 33.33" in errors[0].message
    assert errors[0].code == "VITEST_FAIL"

    assert errors[1].file == "tests/auth.test.ts"
    assert errors[1].line == 50
    assert errors[1].column == 5
    assert "User not found in database" in errors[1].message


@pytest.mark.unit
def test_parse_vitest_output_clean_on_pass() -> None:
    # Arrange
    raw_vitest = """
Test Files  5 passed (5)
Tests  14 passed (14)
Duration  1.23s
"""

    # Act
    errors = parse_vitest_output(raw_vitest)

    # Assert
    assert errors == ()


@pytest.mark.unit
def test_parse_next_build_output_extracts_compilation_errors() -> None:
    # Arrange
    raw_build = """
Failed to compile.

./src/app/expenses/page.tsx:18:24
Type error: Property 'title' does not exist on type 'ExpenseProps'.

./src/components/Nav.tsx
Module not found: Can't resolve '@/components/Icon'
"""

    # Act
    errors = parse_next_build_output(raw_build)

    # Assert
    assert len(errors) == 2
    assert errors[0].file == "src/app/expenses/page.tsx"
    assert errors[0].line == 18
    assert errors[0].column == 24
    assert "Property 'title' does not exist" in errors[0].message

    assert errors[1].file == "src/components/Nav.tsx"
    assert "Module not found" in errors[1].message


@pytest.mark.unit
def test_parse_next_build_output_clean_on_pass() -> None:
    # Arrange
    raw_build = """
   ▲ Next.js 16.0.0
   - Environments: .env.local

 ✓ Compiled successfully
 ✓ Linting and checking validity of types
 ✓ Collecting page data
"""

    # Act
    errors = parse_next_build_output(raw_build)

    # Assert
    assert errors == ()


@pytest.mark.unit
def test_parse_step_output_dispatch_and_success_logic() -> None:
    # Arrange
    clean_output = "Done in 0.5s"
    error_output = "src/index.ts:12:5 - error TS2322: Type mismatch."

    # Act
    clean_result: ValidationStepResult = parse_step_output(
        step=ValidationStep.TYPECHECK,
        raw_output=clean_output,
        exit_code=0,
        duration_ms=500,
    )
    fail_result: ValidationStepResult = parse_step_output(
        step=ValidationStep.TYPECHECK,
        raw_output=error_output,
        exit_code=1,
        duration_ms=450,
    )

    # Assert
    assert clean_result.step == ValidationStep.TYPECHECK
    assert clean_result.success is True
    assert clean_result.exit_code == 0
    assert clean_result.duration_ms == 500
    assert len(clean_result.errors) == 0
    assert clean_result.error_messages == ()

    assert fail_result.step == ValidationStep.TYPECHECK
    assert fail_result.success is False
    assert fail_result.exit_code == 1
    assert len(fail_result.errors) == 1
    assert len(fail_result.error_messages) == 1
    assert "Type mismatch" in fail_result.error_messages[0]


@pytest.mark.unit
def test_parse_validation_output_direct_dispatcher() -> None:
    # Arrange
    output = "src/index.ts:12:5 - error TS2322: Type mismatch."

    # Act
    errors = parse_validation_output(ValidationStep.TYPECHECK, output)

    # Assert
    assert len(errors) == 1
    assert errors[0].file == "src/index.ts"


@pytest.mark.unit
def test_truncate_error_output() -> None:
    # Arrange
    short_text = "Small output"
    long_text = "A" * 10000

    # Act & Assert
    assert truncate_error_output(short_text, max_chars=100) == short_text
    truncated = truncate_error_output(long_text, max_chars=500)
    assert len(truncated) <= 550  # includes truncation notice
    assert "truncated" in truncated.lower()


@pytest.mark.unit
def test_format_validation_errors_for_prompt_groups_by_step() -> None:
    # Arrange
    run_result = ValidationRunResult(
        all_passed=False,
        steps=(
            ValidationStepResult(
                step=ValidationStep.TYPECHECK,
                success=False,
                error_messages=("src/index.ts:12:5 - error TS2322: Type mismatch.",),
            ),
            ValidationStepResult(
                step=ValidationStep.LINT,
                success=True,
            ),
            ValidationStepResult(
                step=ValidationStep.TESTS,
                success=False,
                error_messages=("tests/app.test.ts: AssertionError: expected false to be true",),
            ),
        ),
        error_summary=("Typecheck falló", "Tests fallaron"),
    )

    # Act
    feedback = format_validation_errors_for_prompt(run_result, max_chars=6000)

    # Assert
    assert "### Fallo en paso: TYPECHECK" in feedback
    assert "src/index.ts:12:5 - error TS2322" in feedback
    assert "### Fallo en paso: TESTS" in feedback
    assert "tests/app.test.ts: AssertionError" in feedback
    assert "### Fallo en paso: LINT" not in feedback


@pytest.mark.unit
def test_format_validation_errors_for_prompt_fallback_raw_output() -> None:
    # Arrange
    run_result = ValidationRunResult(
        all_passed=False,
        steps=(
            ValidationStepResult(
                step=ValidationStep.BUILD,
                success=False,
                exit_code=1,
                raw_output="Next.js build failed: missing module './foo'",
            ),
        ),
    )

    # Act
    feedback = format_validation_errors_for_prompt(run_result)

    # Assert
    assert "### Fallo en paso: BUILD" in feedback
    assert "Next.js build failed: missing module './foo'" in feedback


@pytest.mark.unit
def test_format_validation_errors_for_prompt_all_passed() -> None:
    # Arrange
    run_result = ValidationRunResult(
        all_passed=True,
        steps=(
            ValidationStepResult(step=ValidationStep.TYPECHECK, success=True),
            ValidationStepResult(step=ValidationStep.TESTS, success=True),
        ),
    )

    # Act
    feedback = format_validation_errors_for_prompt(run_result)

    # Assert
    assert feedback == ""
