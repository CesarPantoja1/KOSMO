from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kosmo.contracts import (
    CodeWorkspace,
    FeatureImplementation,
    FeatureImplementationStatus,
    FileAction,
    FileOperation,
    ImplementationId,
    ImplementationPlan,
    ValidationErrorDetail,
    ValidationRunResult,
    ValidationSeverity,
    ValidationStep,
    ValidationStepResult,
    WorkspaceId,
    WorkspaceStatus,
)
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.domain.sdd.id_generator import IdGenerator


@pytest.mark.unit
def test_workspace_status_enum_values() -> None:
    assert WorkspaceStatus.NOT_CREATED == "not_created"
    assert WorkspaceStatus.READY == "ready"
    assert WorkspaceStatus.IN_USE == "in_use"
    assert WorkspaceStatus.VALIDATING == "validating"


@pytest.mark.unit
def test_feature_implementation_status_enum_values() -> None:
    assert FeatureImplementationStatus.PENDING == "pending"
    assert FeatureImplementationStatus.IN_PROGRESS == "in_progress"
    assert FeatureImplementationStatus.IMPLEMENTED == "implemented"
    assert FeatureImplementationStatus.REQUIRES_REVIEW == "requires_review"
    assert FeatureImplementationStatus.FAILED == "failed"


@pytest.mark.unit
def test_file_action_enum_values() -> None:
    assert FileAction.CREATE == "create"
    assert FileAction.MODIFY == "modify"
    assert FileAction.DELETE == "delete"


@pytest.mark.unit
def test_validation_step_and_severity_enums() -> None:
    assert ValidationStep.TYPECHECK == "typecheck"
    assert ValidationStep.LINT == "lint"
    assert ValidationStep.TESTS == "tests"
    assert ValidationStep.BUILD == "build"

    assert ValidationSeverity.ERROR == "error"
    assert ValidationSeverity.WARNING == "warning"


@pytest.mark.unit
def test_code_workspace_creation_and_defaults() -> None:
    ws_id = WorkspaceId("ws_01JMABCDEF1234567890ABCDEF")
    prj_id = ProjectId("prj_01JMABCDEF1234567890ABCDEF")

    workspace = CodeWorkspace(id=ws_id, project_id=prj_id)

    assert workspace.id == "ws_01JMABCDEF1234567890ABCDEF"
    assert workspace.project_id == "prj_01JMABCDEF1234567890ABCDEF"
    assert workspace.status == WorkspaceStatus.NOT_CREATED
    assert workspace.workspace_dir is None
    assert workspace.manifest_files == ()
    assert isinstance(workspace.created_at, datetime)
    assert isinstance(workspace.updated_at, datetime)
    assert workspace.created_at.tzinfo == UTC
    assert workspace.updated_at.tzinfo == UTC


@pytest.mark.unit
def test_code_workspace_immutability() -> None:
    workspace = CodeWorkspace(
        id=WorkspaceId("ws_01JMABCDEF1234567890ABCDEF"),
        project_id=ProjectId("prj_01JMABCDEF1234567890ABCDEF"),
        status=WorkspaceStatus.READY,
        workspace_dir="/tmp/workspaces/prj_01",
        manifest_files=("package.json", "tsconfig.json"),
    )

    assert workspace.status == WorkspaceStatus.READY
    assert workspace.workspace_dir == "/tmp/workspaces/prj_01"
    assert workspace.manifest_files == ("package.json", "tsconfig.json")

    with pytest.raises(AttributeError):
        workspace.status = WorkspaceStatus.IN_USE  # type: ignore[misc]

    with pytest.raises(AttributeError):
        workspace.workspace_dir = "/other/dir"  # type: ignore[misc]


@pytest.mark.unit
def test_file_operation_creation_and_immutability() -> None:
    op = FileOperation(
        path="src/components/UserCard.tsx",
        action=FileAction.CREATE,
        description="Componente para visualizar perfil de usuario",
        rationale="Requerido por REQ-1.1",
        target_symbols=("UserCard", "UserCardProps"),
    )

    assert op.path == "src/components/UserCard.tsx"
    assert op.action == FileAction.CREATE
    assert op.description == "Componente para visualizar perfil de usuario"
    assert op.rationale == "Requerido por REQ-1.1"
    assert op.target_symbols == ("UserCard", "UserCardProps")

    with pytest.raises(AttributeError):
        op.action = FileAction.MODIFY  # type: ignore[misc]


@pytest.mark.unit
def test_implementation_plan_creation_and_immutability() -> None:
    op1 = FileOperation(path="src/db/schema.ts", action=FileAction.MODIFY)
    op2 = FileOperation(path="tests/user.test.ts", action=FileAction.CREATE)

    plan = ImplementationPlan(
        feature_id=FeatureId("feat_01JM"),
        operations=(op1, op2),
        summary="Plan para implementar autenticación",
        estimated_effort="2H",
    )

    assert plan.feature_id == "feat_01JM"
    assert len(plan.operations) == 2
    assert plan.operations[0].path == "src/db/schema.ts"
    assert plan.operations[1].action == FileAction.CREATE
    assert plan.summary == "Plan para implementar autenticación"
    assert plan.estimated_effort == "2H"
    assert isinstance(plan.created_at, datetime)

    with pytest.raises(AttributeError):
        plan.summary = "Nuevo plan"  # type: ignore[misc]


@pytest.mark.unit
def test_validation_structures_creation_and_immutability() -> None:
    err1 = ValidationErrorDetail(
        file="src/index.ts",
        line=12,
        column=5,
        message="Type 'string' is not assignable to type 'number'.",
        severity=ValidationSeverity.ERROR,
        code="TS2322",
    )
    assert err1.file == "src/index.ts"
    assert err1.line == 12
    assert err1.column == 5
    assert err1.message == "Type 'string' is not assignable to type 'number'."
    assert err1.severity == ValidationSeverity.ERROR
    assert err1.code == "TS2322"

    with pytest.raises(AttributeError):
        err1.line = 20  # type: ignore[misc]

    step_tc = ValidationStepResult(
        step=ValidationStep.TYPECHECK,
        success=False,
        duration_ms=450,
        exit_code=1,
        raw_output="src/index.ts:12:5 - error TS2322",
        errors=(err1,),
        error_messages=("TS2322: Type 'string' is not assignable to type 'number'.",),
    )
    assert step_tc.step == ValidationStep.TYPECHECK
    assert not step_tc.success
    assert step_tc.duration_ms == 450
    assert len(step_tc.errors) == 1
    assert step_tc.errors[0].file == "src/index.ts"

    with pytest.raises(AttributeError):
        step_tc.success = True  # type: ignore[misc]

    run_result = ValidationRunResult(
        steps=(step_tc,),
        all_passed=False,
        total_duration_ms=450,
        error_summary=("Type check failed with 1 error",),
    )
    assert not run_result.all_passed
    assert run_result.total_duration_ms == 450
    assert len(run_result.steps) == 1
    assert run_result.error_summary == ("Type check failed with 1 error",)
    assert isinstance(run_result.executed_at, datetime)

    with pytest.raises(AttributeError):
        run_result.all_passed = True  # type: ignore[misc]


@pytest.mark.unit
def test_feature_implementation_creation_and_immutability() -> None:
    impl_id = ImplementationId("impl_01JMABCDEF1234567890ABCDEF")
    feat_id = FeatureId("feat_01JMABCDEF1234567890ABCDEF")
    prj_id = ProjectId("prj_01JMABCDEF1234567890ABCDEF")

    plan = ImplementationPlan(
        feature_id=feat_id,
        operations=(FileOperation(path="src/app.ts", action=FileAction.CREATE),),
    )
    validation = ValidationRunResult(all_passed=True, total_duration_ms=1200)

    implementation = FeatureImplementation(
        id=impl_id,
        feature_id=feat_id,
        project_id=prj_id,
        status=FeatureImplementationStatus.IMPLEMENTED,
        session_id="opencode_session_123",
        plan=plan,
        last_validation=validation,
        attempt_count=1,
        max_attempts=3,
        generated_files=("src/app.ts", "tests/app.test.ts"),
    )

    assert implementation.id == "impl_01JMABCDEF1234567890ABCDEF"
    assert implementation.feature_id == "feat_01JMABCDEF1234567890ABCDEF"
    assert implementation.project_id == "prj_01JMABCDEF1234567890ABCDEF"
    assert implementation.status == FeatureImplementationStatus.IMPLEMENTED
    assert implementation.session_id == "opencode_session_123"
    assert implementation.plan == plan
    assert implementation.last_validation == validation
    assert implementation.attempt_count == 1
    assert implementation.max_attempts == 3
    assert implementation.generated_files == ("src/app.ts", "tests/app.test.ts")
    assert isinstance(implementation.created_at, datetime)
    assert isinstance(implementation.updated_at, datetime)

    with pytest.raises(AttributeError):
        implementation.status = FeatureImplementationStatus.FAILED  # type: ignore[misc]


@pytest.mark.unit
def test_id_generator_for_workspace_and_implementation() -> None:
    ws_id = IdGenerator.generate("workspace")
    assert ws_id.startswith("ws_")
    assert len(ws_id) == 3 + 26  # 'ws_' prefix + 26 chars ULID

    code_ws_id = IdGenerator.generate("code_workspace")
    assert code_ws_id.startswith("ws_")

    impl_id = IdGenerator.generate("implementation")
    assert impl_id.startswith("impl_")
    assert len(impl_id) == 5 + 26  # 'impl_' prefix + 26 chars ULID

    feat_impl_id = IdGenerator.generate("feature_implementation")
    assert feat_impl_id.startswith("impl_")
