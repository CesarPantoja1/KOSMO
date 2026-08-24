from __future__ import annotations

import pytest

from kosmo.contracts.sdd.codegen import FileAction, FileOperation, ImplementationPlan
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.domain.codegen.plan_rules import (
    InvalidPlanError,
    PlanRuleViolationType,
    PlanValidationResult,
    ensure_valid_plan,
    validate_plan,
)


@pytest.mark.unit
def test_validate_plan_accepts_valid_operations() -> None:
    # Arrange
    manifest = ("package.json", "tsconfig.json", "src/app.ts")
    plan = ImplementationPlan(
        feature_id=FeatureId("feat_01"),
        operations=(
            FileOperation(path="src/components/Button.tsx", action=FileAction.CREATE),
            FileOperation(path="src/app.ts", action=FileAction.MODIFY),
        ),
        summary="Crea Button.tsx y modifica app.ts",
    )

    # Act
    result: PlanValidationResult = validate_plan(plan, manifest, workspace_root="/workspace")

    # Assert
    assert result.is_valid is True
    assert len(result.violations) == 0
    assert result.error_summary == ()


@pytest.mark.unit
def test_validate_plan_rejects_create_on_existing_file() -> None:
    # Arrange
    manifest = ("package.json", "tsconfig.json", "src/existing.ts")
    plan = ImplementationPlan(
        feature_id=FeatureId("feat_01"),
        operations=(FileOperation(path="src/existing.ts", action=FileAction.CREATE),),
    )

    # Act
    result = validate_plan(plan, manifest, workspace_root="/workspace")

    # Assert
    assert result.is_valid is False
    assert len(result.violations) == 1
    assert result.violations[0].rule == PlanRuleViolationType.FILE_ALREADY_EXISTS
    assert result.violations[0].path == "src/existing.ts"
    assert "ya existe" in result.violations[0].message


@pytest.mark.unit
def test_validate_plan_rejects_modify_on_nonexistent_file() -> None:
    # Arrange
    manifest = ("package.json", "tsconfig.json")
    plan = ImplementationPlan(
        feature_id=FeatureId("feat_01"),
        operations=(FileOperation(path="src/missing.ts", action=FileAction.MODIFY),),
    )

    # Act
    result = validate_plan(plan, manifest, workspace_root="/workspace")

    # Assert
    assert result.is_valid is False
    assert len(result.violations) == 1
    assert result.violations[0].rule == PlanRuleViolationType.FILE_NOT_FOUND
    assert result.violations[0].path == "src/missing.ts"
    assert "no existe" in result.violations[0].message


@pytest.mark.unit
def test_validate_plan_rejects_delete_on_nonexistent_file() -> None:
    # Arrange
    manifest = ("package.json", "tsconfig.json")
    plan = ImplementationPlan(
        feature_id=FeatureId("feat_01"),
        operations=(FileOperation(path="src/nonexistent.ts", action=FileAction.DELETE),),
    )

    # Act
    result = validate_plan(plan, manifest, workspace_root="/workspace")

    # Assert
    assert result.is_valid is False
    assert len(result.violations) == 1
    assert result.violations[0].rule == PlanRuleViolationType.FILE_NOT_FOUND
    assert result.violations[0].path == "src/nonexistent.ts"


@pytest.mark.unit
def test_validate_plan_accepts_delete_on_existing_file() -> None:
    # Arrange
    manifest = ("package.json", "src/old_component.tsx")
    plan = ImplementationPlan(
        feature_id=FeatureId("feat_01"),
        operations=(FileOperation(path="src/old_component.tsx", action=FileAction.DELETE),),
    )

    # Act
    result = validate_plan(plan, manifest, workspace_root="/workspace")

    # Assert
    assert result.is_valid is True
    assert len(result.violations) == 0


@pytest.mark.unit
def test_validate_plan_rejects_delete_on_protected_file() -> None:
    # Arrange
    manifest = ("package.json", "tsconfig.json", "src/index.ts")
    plan = ImplementationPlan(
        feature_id=FeatureId("feat_01"),
        operations=(FileOperation(path="package.json", action=FileAction.DELETE),),
    )

    # Act
    result = validate_plan(plan, manifest, workspace_root="/workspace")

    # Assert
    assert result.is_valid is False
    assert len(result.violations) == 1
    assert result.violations[0].rule == PlanRuleViolationType.PROTECTED_FILE_MODIFICATION
    assert "protegido" in result.violations[0].message


@pytest.mark.unit
def test_validate_plan_rejects_unsafe_paths() -> None:
    # Arrange
    manifest = ("package.json",)
    plan = ImplementationPlan(
        feature_id=FeatureId("feat_01"),
        operations=(
            FileOperation(path="../outside.ts", action=FileAction.CREATE),
            FileOperation(path="/etc/passwd", action=FileAction.CREATE),
        ),
    )

    # Act
    result = validate_plan(plan, manifest, workspace_root="/workspace")

    # Assert
    assert result.is_valid is False
    assert len(result.violations) == 2
    assert all(v.rule == PlanRuleViolationType.UNSAFE_PATH for v in result.violations)


@pytest.mark.unit
def test_validate_plan_rejects_duplicate_operations() -> None:
    # Arrange
    manifest = ("package.json", "src/shared.ts")
    plan = ImplementationPlan(
        feature_id=FeatureId("feat_01"),
        operations=(
            FileOperation(path="src/shared.ts", action=FileAction.MODIFY),
            FileOperation(path="src/shared.ts", action=FileAction.MODIFY),
        ),
    )

    # Act
    result = validate_plan(plan, manifest, workspace_root="/workspace")

    # Assert
    assert result.is_valid is False
    assert any(v.rule == PlanRuleViolationType.DUPLICATE_OPERATION for v in result.violations)


@pytest.mark.unit
def test_validate_plan_rejects_empty_operations() -> None:
    # Arrange
    manifest = ("package.json",)
    plan = ImplementationPlan(
        feature_id=FeatureId("feat_01"),
        operations=(),
    )

    # Act
    result = validate_plan(plan, manifest, workspace_root="/workspace")

    # Assert
    assert result.is_valid is False
    assert len(result.violations) == 1
    assert result.violations[0].rule == PlanRuleViolationType.EMPTY_OPERATIONS


@pytest.mark.unit
def test_ensure_valid_plan_success() -> None:
    # Arrange
    manifest = ("package.json", "src/app.ts")
    plan = ImplementationPlan(
        feature_id=FeatureId("feat_01"),
        operations=(
            FileOperation(path="src/new.ts", action=FileAction.CREATE),
            FileOperation(path="src/app.ts", action=FileAction.MODIFY),
        ),
    )

    # Act
    validated_plan = ensure_valid_plan(plan, manifest, workspace_root="/workspace")

    # Assert
    assert validated_plan == plan


@pytest.mark.unit
def test_ensure_valid_plan_raises_invalid_plan_error() -> None:
    # Arrange
    manifest = ("package.json",)
    plan = ImplementationPlan(
        feature_id=FeatureId("feat_01"),
        operations=(FileOperation(path="src/missing.ts", action=FileAction.MODIFY),),
    )

    # Act & Assert
    with pytest.raises(InvalidPlanError) as exc_info:
        ensure_valid_plan(plan, manifest, workspace_root="/workspace")

    assert "src/missing.ts" in str(exc_info.value)
    assert len(exc_info.value.violations) == 1
