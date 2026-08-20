from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest

from kosmo.contracts import (
    CodeRunnerPort,
    CodeWorkspace,
    FeatureImplementation,
    FeatureImplementationRepository,
    FeatureImplementationStatus,
    FileAction,
    FileOperation,
    ImplementationId,
    ImplementationPlan,
    OpenCodeClientPort,
    OpenCodeEvent,
    OpenCodeEventType,
    OpenCodeSession,
    ValidationErrorDetail,
    ValidationRunResult,
    ValidationSeverity,
    ValidationStep,
    ValidationStepResult,
    WorkspaceId,
    WorkspaceManagerPort,
    WorkspaceRepository,
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


@pytest.mark.unit
def test_opencode_event_type_enum_values() -> None:
    # Arrange & Act & Assert
    assert OpenCodeEventType.SESSION_CREATED == "session_created"
    assert OpenCodeEventType.PLAN_PROGRESS == "plan_progress"
    assert OpenCodeEventType.PLAN_COMPLETE == "plan_complete"
    assert OpenCodeEventType.BUILD_PROGRESS == "build_progress"
    assert OpenCodeEventType.BUILD_COMPLETE == "build_complete"
    assert OpenCodeEventType.FILE_EDIT == "file_edit"
    assert OpenCodeEventType.ERROR == "error"
    assert OpenCodeEventType.DONE == "done"


@pytest.mark.unit
def test_opencode_event_creation_and_immutability() -> None:
    # Arrange
    event = OpenCodeEvent(
        event_type=OpenCodeEventType.PLAN_PROGRESS,
        session_id="session_01",
        data={"step": "analyzing requirements", "progress": 50},
    )

    # Act & Assert
    assert event.event_type == OpenCodeEventType.PLAN_PROGRESS
    assert event.session_id == "session_01"
    assert event.data == {"step": "analyzing requirements", "progress": 50}
    assert isinstance(event.timestamp, datetime)
    assert event.timestamp.tzinfo == UTC

    with pytest.raises(AttributeError):
        event.session_id = "other_session"  # type: ignore[misc]


@pytest.mark.unit
def test_opencode_session_creation_and_immutability() -> None:
    # Arrange
    session = OpenCodeSession(
        session_id="oc_sess_01",
        workspace_dir="/workspaces/prj_01",
        title="Sesión para Feature 1",
    )

    # Act & Assert
    assert session.session_id == "oc_sess_01"
    assert session.workspace_dir == "/workspaces/prj_01"
    assert session.title == "Sesión para Feature 1"
    assert isinstance(session.created_at, datetime)
    assert session.created_at.tzinfo == UTC

    with pytest.raises(AttributeError):
        session.workspace_dir = "/workspaces/prj_02"  # type: ignore[misc]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_workspace_manager_port_protocol_compliance() -> None:
    # Arrange
    class FakeWorkspaceManager:
        def __init__(self) -> None:
            self._workspaces: dict[str, CodeWorkspace] = {}
            self._locked_projects: set[str] = set()

        async def ensure_workspace(self, project_id: ProjectId) -> CodeWorkspace:
            ws = CodeWorkspace(
                id=WorkspaceId(f"ws_{project_id}"),
                project_id=project_id,
                status=WorkspaceStatus.READY,
                workspace_dir=f"/workspaces/{project_id}",
                manifest_files=("package.json", "src/index.ts"),
            )
            self._workspaces[str(project_id)] = ws
            return ws

        async def get_workspace(self, project_id: ProjectId) -> CodeWorkspace | None:
            return self._workspaces.get(str(project_id))

        async def get_manifest(self, workspace: CodeWorkspace) -> tuple[str, ...]:
            return workspace.manifest_files

        async def is_locked(self, project_id: ProjectId) -> bool:
            return str(project_id) in self._locked_projects

        async def acquire_lock(self, project_id: ProjectId) -> None:
            self._locked_projects.add(str(project_id))

        async def release_lock(self, project_id: ProjectId) -> None:
            self._locked_projects.discard(str(project_id))

    manager: WorkspaceManagerPort = FakeWorkspaceManager()
    project_id = ProjectId("prj_01TEST")

    # Act
    workspace = await manager.ensure_workspace(project_id)
    retrieved = await manager.get_workspace(project_id)
    manifest = await manager.get_manifest(workspace)

    is_initially_locked = await manager.is_locked(project_id)
    await manager.acquire_lock(project_id)
    is_locked_after_acquire = await manager.is_locked(project_id)
    await manager.release_lock(project_id)
    is_locked_after_release = await manager.is_locked(project_id)

    # Assert
    assert workspace.status == WorkspaceStatus.READY
    assert retrieved == workspace
    assert manifest == ("package.json", "src/index.ts")
    assert not is_initially_locked
    assert is_locked_after_acquire
    assert not is_locked_after_release


@pytest.mark.asyncio
@pytest.mark.unit
async def test_code_runner_port_protocol_compliance() -> None:
    # Arrange
    class FakeCodeRunner:
        async def run_step(
            self,
            workspace_dir: str,
            step: ValidationStep,
            *,
            timeout_seconds: int = 300,
        ) -> ValidationStepResult:
            return ValidationStepResult(
                step=step,
                success=True,
                duration_ms=120,
                exit_code=0,
                raw_output=f"{step} passed in {workspace_dir}",
            )

        async def run_command(
            self,
            workspace_dir: str,
            command: str,
            *,
            timeout_seconds: int = 300,
        ) -> ValidationStepResult:
            return ValidationStepResult(
                step=ValidationStep.BUILD,
                success=True,
                duration_ms=250,
                exit_code=0,
                raw_output=f"Executed '{command}' in {workspace_dir}",
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
        ) -> ValidationRunResult:
            step_results = tuple(
                ValidationStepResult(
                    step=s,
                    success=True,
                    duration_ms=100,
                    exit_code=0,
                    raw_output="ok",
                )
                for s in steps
            )
            return ValidationRunResult(
                steps=step_results,
                all_passed=True,
                total_duration_ms=100 * len(steps),
            )

    runner: CodeRunnerPort = FakeCodeRunner()

    # Act
    step_result = await runner.run_step("/workspaces/prj_01", ValidationStep.TYPECHECK)
    cmd_result = await runner.run_command("/workspaces/prj_01", "npx vitest run")
    pipeline_result = await runner.run_pipeline(
        "/workspaces/prj_01",
        steps=(ValidationStep.TYPECHECK, ValidationStep.LINT),
    )

    # Assert
    assert step_result.step == ValidationStep.TYPECHECK
    assert step_result.success
    assert cmd_result.success
    assert pipeline_result.all_passed
    assert len(pipeline_result.steps) == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_opencode_client_port_protocol_compliance() -> None:
    # Arrange
    class FakeOpenCodeClient:
        def __init__(self) -> None:
            self._healthy = True
            self._closed_sessions: set[str] = set()

        async def health_check(self) -> bool:
            return self._healthy

        async def create_session(
            self,
            workspace_dir: str,
            *,
            title: str = "",
        ) -> OpenCodeSession:
            return OpenCodeSession(
                session_id="oc_sess_test_01",
                workspace_dir=workspace_dir,
                title=title,
            )

        async def send_prompt(
            self,
            session_id: str,
            prompt: str,
            *,
            agent: str = "plan",
        ) -> AsyncIterator[OpenCodeEvent]:
            yield OpenCodeEvent(
                event_type=OpenCodeEventType.PLAN_PROGRESS,
                session_id=session_id,
                data={"agent": agent, "prompt": prompt},
            )
            yield OpenCodeEvent(
                event_type=OpenCodeEventType.PLAN_COMPLETE,
                session_id=session_id,
                data={"status": "done"},
            )

        async def close_session(self, session_id: str) -> None:
            self._closed_sessions.add(session_id)

    fake_client = FakeOpenCodeClient()
    client: OpenCodeClientPort = fake_client

    # Act
    is_healthy = await client.health_check()
    session = await client.create_session("/workspaces/prj_01", title="Plan Feature")
    events: list[OpenCodeEvent] = []
    async for event in client.send_prompt(session.session_id, "Analiza los requisitos"):
        events.append(event)
    await client.close_session(session.session_id)

    # Assert
    assert is_healthy
    assert session.session_id == "oc_sess_test_01"
    assert session.title == "Plan Feature"
    assert len(events) == 2
    assert events[0].event_type == OpenCodeEventType.PLAN_PROGRESS
    assert events[1].event_type == OpenCodeEventType.PLAN_COMPLETE
    assert session.session_id in fake_client._closed_sessions


@pytest.mark.asyncio
@pytest.mark.unit
async def test_workspace_repository_protocol_compliance() -> None:
    # Arrange
    class FakeWorkspaceRepository:
        def __init__(self) -> None:
            self._by_project: dict[str, CodeWorkspace] = {}
            self._by_id: dict[str, CodeWorkspace] = {}

        async def by_project_id(self, project_id: ProjectId) -> CodeWorkspace | None:
            return self._by_project.get(str(project_id))

        async def by_id(self, workspace_id: WorkspaceId) -> CodeWorkspace | None:
            return self._by_id.get(str(workspace_id))

        async def save(self, workspace: CodeWorkspace) -> CodeWorkspace:
            self._by_project[str(workspace.project_id)] = workspace
            self._by_id[str(workspace.id)] = workspace
            return workspace

        async def delete(self, project_id: ProjectId) -> None:
            ws = self._by_project.pop(str(project_id), None)
            if ws:
                self._by_id.pop(str(ws.id), None)

        async def update_lock(
            self,
            project_id: ProjectId,
            is_locked: bool,
            locked_by: str | None = None,
        ) -> CodeWorkspace | None:
            ws = self._by_project.get(str(project_id))
            if ws is None:
                return None
            return ws

        async def release_lock(self, project_id: ProjectId) -> CodeWorkspace | None:
            return await self.update_lock(project_id, is_locked=False)

    repo: WorkspaceRepository = FakeWorkspaceRepository()

    project_id = ProjectId("prj_01TEST")
    workspace = CodeWorkspace(
        id=WorkspaceId("ws_01TEST"),
        project_id=project_id,
        status=WorkspaceStatus.READY,
    )

    # Act
    saved = await repo.save(workspace)
    found_by_prj = await repo.by_project_id(project_id)
    found_by_id = await repo.by_id(WorkspaceId("ws_01TEST"))
    await repo.delete(project_id)
    after_delete = await repo.by_project_id(project_id)

    # Assert
    assert saved == workspace
    assert found_by_prj == workspace
    assert found_by_id == workspace
    assert after_delete is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_feature_implementation_repository_protocol_compliance() -> None:
    # Arrange
    class FakeFeatureImplementationRepository:
        def __init__(self) -> None:
            self._by_feature: dict[str, FeatureImplementation] = {}
            self._by_id: dict[str, FeatureImplementation] = {}

        async def by_feature_id(self, feature_id: FeatureId) -> FeatureImplementation | None:
            return self._by_feature.get(str(feature_id))

        async def by_id(self, implementation_id: ImplementationId) -> FeatureImplementation | None:
            return self._by_id.get(str(implementation_id))

        async def list_by_project(self, project_id: ProjectId) -> list[FeatureImplementation]:
            return [impl for impl in self._by_feature.values() if impl.project_id == project_id]

        async def save(self, implementation: FeatureImplementation) -> FeatureImplementation:
            self._by_feature[str(implementation.feature_id)] = implementation
            self._by_id[str(implementation.id)] = implementation
            return implementation

        async def delete(self, feature_id: FeatureId) -> None:
            impl = self._by_feature.pop(str(feature_id), None)
            if impl:
                self._by_id.pop(str(impl.id), None)

    repo: FeatureImplementationRepository = FakeFeatureImplementationRepository()
    feat_id = FeatureId("feat_01TEST")
    prj_id = ProjectId("prj_01TEST")
    impl = FeatureImplementation(
        id=ImplementationId("impl_01TEST"),
        feature_id=feat_id,
        project_id=prj_id,
        status=FeatureImplementationStatus.IN_PROGRESS,
    )

    # Act
    saved = await repo.save(impl)
    found_by_feat = await repo.by_feature_id(feat_id)
    found_by_id = await repo.by_id(ImplementationId("impl_01TEST"))
    list_result = await repo.list_by_project(prj_id)
    await repo.delete(feat_id)
    after_delete = await repo.by_feature_id(feat_id)

    # Assert
    assert saved == impl
    assert found_by_feat == impl
    assert found_by_id == impl
    assert list_result == [impl]
    assert after_delete is None
