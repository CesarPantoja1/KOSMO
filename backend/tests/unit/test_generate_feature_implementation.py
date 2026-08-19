from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from kosmo.application.codegen.generate_feature_implementation import (
    GenerateFeatureImplementationInput,
    GenerateFeatureImplementationUseCase,
    MissingDiagramError,
    MissingRequirementsError,
)
from kosmo.contracts.codegen import (
    CodeRunnerPort,
    CodeWorkspace,
    FeatureImplementation,
    FeatureImplementationRepository,
    FeatureImplementationStatus,
    FileAction,
    FileOperation,
    OpenCodeClientPort,
    OpenCodeEvent,
    OpenCodeEventType,
    OpenCodeSession,
    ValidationErrorDetail,
    ValidationRunResult,
    ValidationSeverity,
    ValidationStep,
    ValidationStepResult,
    WorkspaceManagerPort,
    WorkspaceStatus,
)
from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import (
    ActivityDiagramId,
    FeatureId,
    ImplementationId,
    ProjectId,
    WorkspaceId,
)
from kosmo.infrastructure.codegen.workspace import WorkspaceLockedError
from tests.unit.fakes import (
    InMemoryActivityDiagramRepository,
    InMemoryFeatureRepository,
    InMemoryRequirementRepository,
    InMemoryTraceabilityRepository,
)


class FakeWorkspaceManager(WorkspaceManagerPort):
    def __init__(self, workspace_dir: str = "/workspaces/prj_01") -> None:
        self.workspace_dir = workspace_dir
        self.locked_projects: set[str] = set()
        self.rollback_called_for: set[str] = set()
        self.commit_called_for: list[tuple[str, str]] = []
        self.manifest: tuple[str, ...] = ("package.json", "tsconfig.json", "src/index.ts")

    async def ensure_workspace(self, project_id: ProjectId) -> CodeWorkspace:
        return CodeWorkspace(
            id=WorkspaceId(f"ws_{project_id}"),
            project_id=project_id,
            status=WorkspaceStatus.READY,
            workspace_dir=self.workspace_dir,
            manifest_files=self.manifest,
        )

    async def get_workspace(self, project_id: ProjectId) -> CodeWorkspace | None:
        return await self.ensure_workspace(project_id)

    async def get_manifest(self, workspace: CodeWorkspace) -> tuple[str, ...]:
        return self.manifest

    async def is_locked(self, project_id: ProjectId) -> bool:
        return str(project_id) in self.locked_projects

    async def acquire_lock(self, project_id: ProjectId) -> None:
        if str(project_id) in self.locked_projects:
            raise WorkspaceLockedError(f"Workspace {project_id} already locked")
        self.locked_projects.add(str(project_id))

    async def release_lock(self, project_id: ProjectId) -> None:
        self.locked_projects.discard(str(project_id))

    async def rollback_workspace(self, project_id: ProjectId) -> None:
        self.rollback_called_for.add(str(project_id))

    async def commit_workspace(self, project_id: ProjectId, message: str) -> bool:
        self.commit_called_for.append((str(project_id), message))
        return True


class FakeOpenCodeClient(OpenCodeClientPort):
    def __init__(self) -> None:
        self.closed_sessions: set[str] = set()
        self.created_sessions: list[OpenCodeSession] = []
        self.prompts_sent: list[tuple[str, str, str]] = []
        self.plan_operations: tuple[FileOperation, ...] = (
            FileOperation(path="src/calc.ts", action=FileAction.CREATE),
            FileOperation(path="tests/calc.test.ts", action=FileAction.CREATE),
        )

    async def health_check(self) -> bool:
        return True

    async def create_session(self, workspace_dir: str, *, title: str = "") -> OpenCodeSession:
        session = OpenCodeSession(
            session_id=f"oc_sess_{len(self.created_sessions) + 1}",
            workspace_dir=workspace_dir,
            title=title,
        )
        self.created_sessions.append(session)
        return session

    async def send_prompt(
        self,
        session_id: str,
        prompt: str,
        *,
        agent: str = "plan",
    ) -> AsyncIterator[OpenCodeEvent]:
        self.prompts_sent.append((session_id, prompt, agent))
        if agent == "plan":
            yield OpenCodeEvent(
                event_type=OpenCodeEventType.PLAN_PROGRESS,
                session_id=session_id,
                data={"delta": "Analizando estructura..."},
            )
            yield OpenCodeEvent(
                event_type=OpenCodeEventType.PLAN_COMPLETE,
                session_id=session_id,
                data={
                    "plan": "CREATE src/calc.ts\nCREATE tests/calc.test.ts",
                    "operations": [
                        {"path": "src/calc.ts", "action": "create"},
                        {"path": "tests/calc.test.ts", "action": "create"},
                    ],
                },
            )
        elif agent == "build":
            yield OpenCodeEvent(
                event_type=OpenCodeEventType.BUILD_PROGRESS,
                session_id=session_id,
                data={"delta": "Generando archivos..."},
            )
            yield OpenCodeEvent(
                event_type=OpenCodeEventType.FILE_EDIT,
                session_id=session_id,
                data={"path": "src/calc.ts", "action": "create"},
            )
            yield OpenCodeEvent(
                event_type=OpenCodeEventType.BUILD_COMPLETE,
                session_id=session_id,
                data={"status": "success", "files": ["src/calc.ts", "tests/calc.test.ts"]},
            )

    async def close_session(self, session_id: str) -> None:
        self.closed_sessions.add(session_id)


class FakeCodeRunner(CodeRunnerPort):
    def __init__(self, should_pass: bool = True, fail_count_before_pass: int = 0) -> None:
        self.should_pass = should_pass
        self.fail_count_before_pass = fail_count_before_pass
        self.runs_count = 0

    async def run_step(
        self,
        workspace_dir: str,
        step: ValidationStep,
        *,
        timeout_seconds: int = 300,
    ) -> ValidationStepResult:
        return ValidationStepResult(step=step, success=True)

    async def run_command(
        self,
        workspace_dir: str,
        command: str,
        *,
        timeout_seconds: int = 300,
    ) -> ValidationStepResult:
        return ValidationStepResult(step=ValidationStep.TYPECHECK, success=True)

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
        self.runs_count += 1
        if self.fail_count_before_pass > 0 and self.runs_count <= self.fail_count_before_pass:
            return ValidationRunResult(
                all_passed=False,
                steps=(
                    ValidationStepResult(
                        step=ValidationStep.TYPECHECK,
                        success=False,
                        errors=(
                            ValidationErrorDetail(
                                file="src/calc.ts",
                                line=10,
                                column=5,
                                message="Cannot find name 'result'",
                                severity=ValidationSeverity.ERROR,
                            ),
                        ),
                        error_messages=("src/calc.ts:10:5 - error TS2304: Cannot find name 'result'",),
                    ),
                ),
                error_summary=("Typecheck falló con 1 error",),
            )

        if not self.should_pass:
            return ValidationRunResult(
                all_passed=False,
                steps=(
                    ValidationStepResult(
                        step=ValidationStep.TESTS,
                        success=False,
                        error_messages=("AssertionError: expected 5 to be 10",),
                    ),
                ),
                error_summary=("Tests fallaron",),
            )

        return ValidationRunResult(
            all_passed=True,
            steps=tuple(ValidationStepResult(step=s, success=True) for s in steps),
        )


class FakeFeatureImplementationRepository(FeatureImplementationRepository):
    def __init__(self) -> None:
        self.implementations: dict[str, FeatureImplementation] = {}

    async def by_feature_id(self, feature_id: FeatureId) -> FeatureImplementation | None:
        return self.implementations.get(str(feature_id))

    async def by_id(self, implementation_id: ImplementationId) -> FeatureImplementation | None:
        return next((impl for impl in self.implementations.values() if impl.id == implementation_id), None)

    async def list_by_project(self, project_id: ProjectId) -> list[FeatureImplementation]:
        return [impl for impl in self.implementations.values() if impl.project_id == project_id]

    async def save(self, implementation: FeatureImplementation) -> FeatureImplementation:
        self.implementations[str(implementation.feature_id)] = implementation
        return implementation

    async def delete(self, feature_id: FeatureId) -> None:
        self.implementations.pop(str(feature_id), None)


class RaisingTraceabilityRepository(InMemoryTraceabilityRepository):
    async def add_edge(self, *args: object, **kwargs: object) -> None:
        raise RuntimeError("db down")

    async def delete_by_entity_id(self, entity_id: str) -> None:
        raise RuntimeError("db down")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_feature_implementation_success() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    activity_diagram_repo = InMemoryActivityDiagramRepository()
    workspace_manager = FakeWorkspaceManager()
    opencode_client = FakeOpenCodeClient()
    code_runner = FakeCodeRunner(should_pass=True)
    impl_repo = FakeFeatureImplementationRepository()
    trace_repo = InMemoryTraceabilityRepository()

    feat_id = FeatureId("feat_01HT_GASTOS")
    prj_id = ProjectId("prj_01HT_APP")
    feature = Feature(
        id=feat_id,
        number=1,
        title="Registrar gastos",
        slug="registrar-gastos",
        description="Permite registrar transacciones de gastos",
        project_id=prj_id,
    )
    await feature_repo.save(feature)
    await requirement_repo.save(feat_id, "# REQ-1.1: El sistema registrará los gastos")
    await activity_diagram_repo.save(
        DiagramaActividad(
            id=ActivityDiagramId("diag_01"),
            feature_id=feat_id,
            diagram_syntax="@startuml\nstart\n:Registrar gasto;\nstop\n@enduml",
        )
    )

    use_case = GenerateFeatureImplementationUseCase(
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        activity_diagram_repo=activity_diagram_repo,
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
        implementation_repo=impl_repo,
        traceability_repo=trace_repo,
    )

    # Act
    output = await use_case.execute(GenerateFeatureImplementationInput(feature_id=feat_id))

    # Assert
    assert output.success is True
    assert output.status == FeatureImplementationStatus.IMPLEMENTED
    assert output.implementation is not None
    assert output.implementation.status == FeatureImplementationStatus.IMPLEMENTED
    assert output.workspace is not None
    assert output.validation_result is not None
    assert output.validation_result.all_passed is True
    assert "src/calc.ts" in output.generated_files
    assert len(opencode_client.closed_sessions) == 1
    assert len(workspace_manager.commit_called_for) == 1
    assert workspace_manager.commit_called_for[0][0] == str(prj_id)
    assert "C01" in workspace_manager.commit_called_for[0][1]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_feature_implementation_raises_when_feature_not_found() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    activity_diagram_repo = InMemoryActivityDiagramRepository()
    workspace_manager = FakeWorkspaceManager()
    opencode_client = FakeOpenCodeClient()
    code_runner = FakeCodeRunner()
    impl_repo = FakeFeatureImplementationRepository()
    trace_repo = InMemoryTraceabilityRepository()

    use_case = GenerateFeatureImplementationUseCase(
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        activity_diagram_repo=activity_diagram_repo,
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
        implementation_repo=impl_repo,
        traceability_repo=trace_repo,
    )

    # Act & Assert
    with pytest.raises(FeatureNotFoundError) as exc_info:
        await use_case.execute(GenerateFeatureImplementationInput(feature_id=FeatureId("feat_missing")))

    assert "feat_missing" in str(exc_info.value.problem.detail)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_feature_implementation_raises_when_requirements_missing() -> None:
    # Arrange (CA-02: Generación fallida por falta de requisitos)
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    activity_diagram_repo = InMemoryActivityDiagramRepository()
    workspace_manager = FakeWorkspaceManager()
    opencode_client = FakeOpenCodeClient()
    code_runner = FakeCodeRunner()
    impl_repo = FakeFeatureImplementationRepository()
    trace_repo = InMemoryTraceabilityRepository()

    feat_id = FeatureId("feat_02_NOTIF")
    prj_id = ProjectId("prj_01")
    feature = Feature(
        id=feat_id,
        number=2,
        title="Notificar vencimientos",
        slug="notificar-vencimientos",
        description="Envía notificaciones",
        project_id=prj_id,
    )
    await feature_repo.save(feature)
    # Requisitos NO generados

    use_case = GenerateFeatureImplementationUseCase(
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        activity_diagram_repo=activity_diagram_repo,
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
        implementation_repo=impl_repo,
        traceability_repo=trace_repo,
    )

    # Act & Assert
    with pytest.raises(MissingRequirementsError) as exc_info:
        await use_case.execute(GenerateFeatureImplementationInput(feature_id=feat_id))

    expected_msg = "Esta característica no tiene requisitos EARS generados. Genera los requisitos antes de continuar."
    assert expected_msg in str(exc_info.value)
    assert await workspace_manager.is_locked(prj_id) is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_feature_implementation_raises_when_activity_diagram_missing() -> None:
    # Arrange (CA-03: Generación fallida por falta de diagrama)
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    activity_diagram_repo = InMemoryActivityDiagramRepository()
    workspace_manager = FakeWorkspaceManager()
    opencode_client = FakeOpenCodeClient()
    code_runner = FakeCodeRunner()
    impl_repo = FakeFeatureImplementationRepository()
    trace_repo = InMemoryTraceabilityRepository()

    feat_id = FeatureId("feat_03_EXP")
    prj_id = ProjectId("prj_01")
    feature = Feature(
        id=feat_id,
        number=3,
        title="Exportar reportes",
        slug="exportar-reportes",
        description="Exporta datos en PDF",
        project_id=prj_id,
    )
    await feature_repo.save(feature)
    await requirement_repo.save(feat_id, "# REQ-3.1: Exportar")
    # Diagrama de actividad NO generado

    use_case = GenerateFeatureImplementationUseCase(
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        activity_diagram_repo=activity_diagram_repo,
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
        implementation_repo=impl_repo,
        traceability_repo=trace_repo,
    )

    # Act & Assert
    with pytest.raises(MissingDiagramError) as exc_info:
        await use_case.execute(GenerateFeatureImplementationInput(feature_id=feat_id))

    expected_msg = "Esta característica no tiene diagrama de actividad generado. Genera el diagrama antes de continuar."
    assert expected_msg in str(exc_info.value)
    assert await workspace_manager.is_locked(prj_id) is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_feature_implementation_retries_on_validation_failure_and_succeeds() -> None:
    # Arrange (Reintento de validación con retroalimentación)
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    activity_diagram_repo = InMemoryActivityDiagramRepository()
    workspace_manager = FakeWorkspaceManager()
    opencode_client = FakeOpenCodeClient()
    code_runner = FakeCodeRunner(fail_count_before_pass=1)  # Falla en intento 1, pasa en intento 2
    impl_repo = FakeFeatureImplementationRepository()
    trace_repo = InMemoryTraceabilityRepository()

    feat_id = FeatureId("feat_04_CALC")
    prj_id = ProjectId("prj_01")
    feature = Feature(
        id=feat_id,
        number=4,
        title="Calcular balances",
        slug="calcular-balances",
        description="Calcula balances",
        project_id=prj_id,
    )
    await feature_repo.save(feature)
    await requirement_repo.save(feat_id, "# REQ-4.1: Calcular")
    await activity_diagram_repo.save(
        DiagramaActividad(
            id=ActivityDiagramId("diag_04"),
            feature_id=feat_id,
            diagram_syntax="@startuml\nstop\n@enduml",
        )
    )

    use_case = GenerateFeatureImplementationUseCase(
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        activity_diagram_repo=activity_diagram_repo,
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
        implementation_repo=impl_repo,
        traceability_repo=trace_repo,
    )

    # Act
    output = await use_case.execute(GenerateFeatureImplementationInput(feature_id=feat_id, max_retries=3))

    # Assert
    assert output.success is True
    assert output.status == FeatureImplementationStatus.IMPLEMENTED
    assert output.implementation is not None
    assert output.implementation.attempt_count == 2
    assert code_runner.runs_count == 2
    assert len(opencode_client.prompts_sent) == 3  # plan + initial build + fix build
    assert await workspace_manager.is_locked(prj_id) is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_feature_implementation_exhausts_retries_and_marks_requires_review() -> None:
    # Arrange (CA-04: Generación fallida tras agotar correcciones)
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    activity_diagram_repo = InMemoryActivityDiagramRepository()
    workspace_manager = FakeWorkspaceManager()
    opencode_client = FakeOpenCodeClient()
    code_runner = FakeCodeRunner(should_pass=False)  # Siempre falla
    impl_repo = FakeFeatureImplementationRepository()
    trace_repo = InMemoryTraceabilityRepository()

    feat_id = FeatureId("feat_05_FAIL")
    prj_id = ProjectId("prj_01")
    feature = Feature(
        id=feat_id,
        number=5,
        title="Calcular balances complejos",
        slug="calcular-balances-complejos",
        description="Falla en validaciones",
        project_id=prj_id,
    )
    await feature_repo.save(feature)
    await requirement_repo.save(feat_id, "# REQ-5.1: Fail")
    await activity_diagram_repo.save(
        DiagramaActividad(
            id=ActivityDiagramId("diag_05"),
            feature_id=feat_id,
            diagram_syntax="@startuml\nstop\n@enduml",
        )
    )

    use_case = GenerateFeatureImplementationUseCase(
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        activity_diagram_repo=activity_diagram_repo,
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
        implementation_repo=impl_repo,
        traceability_repo=trace_repo,
    )

    # Act
    output = await use_case.execute(GenerateFeatureImplementationInput(feature_id=feat_id, max_retries=3))

    # Assert
    assert output.success is False
    assert output.status == FeatureImplementationStatus.REQUIRES_REVIEW
    assert output.implementation is not None
    assert output.implementation.status == FeatureImplementationStatus.REQUIRES_REVIEW
    assert output.implementation.attempt_count == 3
    assert code_runner.runs_count == 3
    assert await workspace_manager.is_locked(prj_id) is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_feature_implementation_execute_stream_yields_events() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    activity_diagram_repo = InMemoryActivityDiagramRepository()
    workspace_manager = FakeWorkspaceManager()
    opencode_client = FakeOpenCodeClient()
    code_runner = FakeCodeRunner(should_pass=True)
    impl_repo = FakeFeatureImplementationRepository()
    trace_repo = InMemoryTraceabilityRepository()

    feat_id = FeatureId("feat_06_STREAM")
    prj_id = ProjectId("prj_01")
    feature = Feature(
        id=feat_id,
        number=6,
        title="Stream test",
        slug="stream-test",
        description="Streaming",
        project_id=prj_id,
    )
    await feature_repo.save(feature)
    await requirement_repo.save(feat_id, "# REQ-6.1: Stream")
    await activity_diagram_repo.save(
        DiagramaActividad(
            id=ActivityDiagramId("diag_06"),
            feature_id=feat_id,
            diagram_syntax="@startuml\nstop\n@enduml",
        )
    )

    use_case = GenerateFeatureImplementationUseCase(
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        activity_diagram_repo=activity_diagram_repo,
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
        implementation_repo=impl_repo,
        traceability_repo=trace_repo,
    )

    # Act
    events: list[OpenCodeEvent] = []
    async for event in use_case.execute_stream(GenerateFeatureImplementationInput(feature_id=feat_id)):
        events.append(event)

    # Assert
    assert len(events) > 0
    event_types = [e.event_type for e in events]
    assert OpenCodeEventType.PLAN_PROGRESS in event_types
    assert OpenCodeEventType.PLAN_COMPLETE in event_types
    assert OpenCodeEventType.BUILD_PROGRESS in event_types
    assert OpenCodeEventType.BUILD_COMPLETE in event_types
    assert OpenCodeEventType.DONE in event_types


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_feature_implementation_always_releases_lock_on_error() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    activity_diagram_repo = InMemoryActivityDiagramRepository()
    workspace_manager = FakeWorkspaceManager()

    class CrashingOpenCodeClient(FakeOpenCodeClient):
        async def create_session(self, workspace_dir: str, *, title: str = "") -> OpenCodeSession:
            raise RuntimeError("OpenCode server crashed unexpectedly")

    opencode_client = CrashingOpenCodeClient()
    code_runner = FakeCodeRunner()
    impl_repo = FakeFeatureImplementationRepository()
    trace_repo = InMemoryTraceabilityRepository()

    feat_id = FeatureId("feat_07_CRASH")
    prj_id = ProjectId("prj_01")
    feature = Feature(
        id=feat_id,
        number=7,
        title="Crash test",
        slug="crash-test",
        description="Crash",
        project_id=prj_id,
    )
    await feature_repo.save(feature)
    await requirement_repo.save(feat_id, "# REQ-7.1: Crash")
    await activity_diagram_repo.save(
        DiagramaActividad(
            id=ActivityDiagramId("diag_07"),
            feature_id=feat_id,
            diagram_syntax="@startuml\nstop\n@enduml",
        )
    )

    use_case = GenerateFeatureImplementationUseCase(
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        activity_diagram_repo=activity_diagram_repo,
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
        implementation_repo=impl_repo,
        traceability_repo=trace_repo,
    )

    # Act & Assert
    with pytest.raises(RuntimeError):
        await use_case.execute(GenerateFeatureImplementationInput(feature_id=feat_id))

    assert await workspace_manager.is_locked(prj_id) is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_retry_emits_retry_events() -> None:
    """T17: Verificar que se emitan eventos RETRY con los errores parseados en cada reintento."""
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    activity_diagram_repo = InMemoryActivityDiagramRepository()
    workspace_manager = FakeWorkspaceManager()
    opencode_client = FakeOpenCodeClient()
    code_runner = FakeCodeRunner(fail_count_before_pass=2)  # Falla 2 veces, pasa en el 3ro
    impl_repo = FakeFeatureImplementationRepository()
    trace_repo = InMemoryTraceabilityRepository()

    feat_id = FeatureId("feat_T17_RETRY_EVENTS")
    prj_id = ProjectId("prj_01")
    feature = Feature(
        id=feat_id,
        number=17,
        title="Retry events test",
        slug="retry-events-test",
        description="Test retry events",
        project_id=prj_id,
    )
    await feature_repo.save(feature)
    await requirement_repo.save(feat_id, "# REQ-17.1: Retry")
    await activity_diagram_repo.save(
        DiagramaActividad(
            id=ActivityDiagramId("diag_17"),
            feature_id=feat_id,
            diagram_syntax="@startuml\nstop\n@enduml",
        )
    )

    use_case = GenerateFeatureImplementationUseCase(
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        activity_diagram_repo=activity_diagram_repo,
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
        implementation_repo=impl_repo,
        traceability_repo=trace_repo,
    )

    output = await use_case.execute(GenerateFeatureImplementationInput(feature_id=feat_id, max_retries=3))

    assert output.success is True
    retry_events = [e for e in output.events if e.event_type == OpenCodeEventType.RETRY]
    assert len(retry_events) == 2
    assert retry_events[0].data["attempt"] == 1
    assert retry_events[1].data["attempt"] == 2
    assert "error_summary" in retry_events[0].data


@pytest.mark.asyncio
@pytest.mark.unit
async def test_exhausted_retries_calls_rollback() -> None:
    """T17: Verificar que al agotar reintentos se invoque rollback_workspace."""
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    activity_diagram_repo = InMemoryActivityDiagramRepository()
    workspace_manager = FakeWorkspaceManager()
    opencode_client = FakeOpenCodeClient()
    code_runner = FakeCodeRunner(should_pass=False)
    impl_repo = FakeFeatureImplementationRepository()
    trace_repo = InMemoryTraceabilityRepository()

    feat_id = FeatureId("feat_T17_ROLLBACK")
    prj_id = ProjectId("prj_01")
    feature = Feature(
        id=feat_id,
        number=18,
        title="Rollback test",
        slug="rollback-test",
        description="Test rollback",
        project_id=prj_id,
    )
    await feature_repo.save(feature)
    await requirement_repo.save(feat_id, "# REQ-18.1: Rollback")
    await activity_diagram_repo.save(
        DiagramaActividad(
            id=ActivityDiagramId("diag_18"),
            feature_id=feat_id,
            diagram_syntax="@startuml\nstop\n@enduml",
        )
    )

    use_case = GenerateFeatureImplementationUseCase(
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        activity_diagram_repo=activity_diagram_repo,
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
        implementation_repo=impl_repo,
        traceability_repo=trace_repo,
    )

    output = await use_case.execute(GenerateFeatureImplementationInput(feature_id=feat_id, max_retries=3))

    assert output.success is False
    assert output.status == FeatureImplementationStatus.REQUIRES_REVIEW
    assert str(prj_id) in workspace_manager.rollback_called_for


@pytest.mark.asyncio
@pytest.mark.unit
async def test_retry_history_accumulated() -> None:
    """T17: Verificar que el historial de errores por intento se acumule correctamente."""
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    activity_diagram_repo = InMemoryActivityDiagramRepository()
    workspace_manager = FakeWorkspaceManager()
    opencode_client = FakeOpenCodeClient()
    code_runner = FakeCodeRunner(should_pass=False)
    impl_repo = FakeFeatureImplementationRepository()
    trace_repo = InMemoryTraceabilityRepository()

    feat_id = FeatureId("feat_T17_HISTORY")
    prj_id = ProjectId("prj_01")
    feature = Feature(
        id=feat_id,
        number=19,
        title="History test",
        slug="history-test",
        description="Test history",
        project_id=prj_id,
    )
    await feature_repo.save(feature)
    await requirement_repo.save(feat_id, "# REQ-19.1: History")
    await activity_diagram_repo.save(
        DiagramaActividad(
            id=ActivityDiagramId("diag_19"),
            feature_id=feat_id,
            diagram_syntax="@startuml\nstop\n@enduml",
        )
    )

    use_case = GenerateFeatureImplementationUseCase(
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        activity_diagram_repo=activity_diagram_repo,
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
        implementation_repo=impl_repo,
        traceability_repo=trace_repo,
    )

    output = await use_case.execute(GenerateFeatureImplementationInput(feature_id=feat_id, max_retries=3))

    assert output.success is False
    assert len(output.retry_history) == 3
    assert output.implementation is not None
    assert len(output.implementation.retry_history) == 3
    for errors in output.retry_history:
        assert len(errors) > 0
    assert "Intento 1" in (output.error_message or "")
    assert len(trace_repo.edges) == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_prompt_incluye_plan_y_requisitos() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    activity_diagram_repo = InMemoryActivityDiagramRepository()
    workspace_manager = FakeWorkspaceManager()
    opencode_client = FakeOpenCodeClient()
    code_runner = FakeCodeRunner(should_pass=True)
    impl_repo = FakeFeatureImplementationRepository()
    trace_repo = InMemoryTraceabilityRepository()

    feat_id = FeatureId("feat_01HT_GASTOS")
    prj_id = ProjectId("prj_01HT_APP")
    feature = Feature(
        id=feat_id,
        number=1,
        title="Registrar gastos",
        slug="registrar-gastos",
        description="Permite registrar transacciones de gastos",
        project_id=prj_id,
    )
    await feature_repo.save(feature)
    await requirement_repo.save(feat_id, "# REQ-1.1: El sistema registrará los gastos")
    await activity_diagram_repo.save(
        DiagramaActividad(
            id=ActivityDiagramId("diag_01"),
            feature_id=feat_id,
            diagram_syntax="@startuml\nstart\n:Registrar gasto;\nstop\n@enduml",
        )
    )

    use_case = GenerateFeatureImplementationUseCase(
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        activity_diagram_repo=activity_diagram_repo,
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
        implementation_repo=impl_repo,
        traceability_repo=trace_repo,
    )

    # Act
    await use_case.execute(GenerateFeatureImplementationInput(feature_id=feat_id))

    # Assert
    build_prompts = [prompt for (_, prompt, agent) in opencode_client.prompts_sent if agent == "build"]
    assert len(build_prompts) == 1
    build_prompt = build_prompts[0]
    assert "# REQ-1.1: El sistema registrará los gastos" in build_prompt
    assert "Plan aprobado" in build_prompt
    assert "[create] src/calc.ts" in build_prompt
    assert "[create] tests/calc.test.ts" in build_prompt


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_registers_traceability_post_commit() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    activity_diagram_repo = InMemoryActivityDiagramRepository()
    workspace_manager = FakeWorkspaceManager()
    opencode_client = FakeOpenCodeClient()
    code_runner = FakeCodeRunner(should_pass=True)
    impl_repo = FakeFeatureImplementationRepository()
    trace_repo = InMemoryTraceabilityRepository()

    feat_id = FeatureId("feat_01HT_GASTOS")
    prj_id = ProjectId("prj_01HT_APP")
    feature = Feature(
        id=feat_id,
        number=1,
        title="Registrar gastos",
        slug="registrar-gastos",
        description="Permite registrar transacciones de gastos",
        project_id=prj_id,
    )
    await feature_repo.save(feature)
    await requirement_repo.save(feat_id, "# REQ-1.1: El sistema registrará los gastos")
    await activity_diagram_repo.save(
        DiagramaActividad(
            id=ActivityDiagramId("diag_01"),
            feature_id=feat_id,
            diagram_syntax="@startuml\nstart\n:Registrar gasto;\nstop\n@enduml",
        )
    )

    use_case = GenerateFeatureImplementationUseCase(
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        activity_diagram_repo=activity_diagram_repo,
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
        implementation_repo=impl_repo,
        traceability_repo=trace_repo,
    )

    # Act
    output = await use_case.execute(GenerateFeatureImplementationInput(feature_id=feat_id))

    # Assert
    assert output.success is True
    assert ("feature", str(feat_id), "code_file", "src/calc.ts", "codegen") in trace_repo.edges
    assert ("feature", str(feat_id), "test_file", "tests/calc.test.ts", "codegen") in trace_repo.edges
    assert ("requirement", f"{feat_id}:REQ-1.1", "code_file", "src/calc.ts", "codegen") in trace_repo.edges
    assert ("requirement", f"{feat_id}:REQ-1.1", "test_file", "tests/calc.test.ts", "codegen") in trace_repo.edges
    done_events = [e for e in output.events if e.event_type == OpenCodeEventType.DONE]
    assert len(done_events) == 1
    assert done_events[0].data.get("traceability_edges") == 4


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_emits_error_event_si_trazabilidad_falla() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    activity_diagram_repo = InMemoryActivityDiagramRepository()
    workspace_manager = FakeWorkspaceManager()
    opencode_client = FakeOpenCodeClient()
    code_runner = FakeCodeRunner(should_pass=True)
    impl_repo = FakeFeatureImplementationRepository()
    trace_repo = RaisingTraceabilityRepository()

    feat_id = FeatureId("feat_01HT_GASTOS")
    prj_id = ProjectId("prj_01HT_APP")
    feature = Feature(
        id=feat_id,
        number=1,
        title="Registrar gastos",
        slug="registrar-gastos",
        description="Permite registrar transacciones de gastos",
        project_id=prj_id,
    )
    await feature_repo.save(feature)
    await requirement_repo.save(feat_id, "# REQ-1.1: El sistema registrará los gastos")
    await activity_diagram_repo.save(
        DiagramaActividad(
            id=ActivityDiagramId("diag_01"),
            feature_id=feat_id,
            diagram_syntax="@startuml\nstart\n:Registrar gasto;\nstop\n@enduml",
        )
    )

    use_case = GenerateFeatureImplementationUseCase(
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        activity_diagram_repo=activity_diagram_repo,
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
        implementation_repo=impl_repo,
        traceability_repo=trace_repo,
    )

    # Act
    output = await use_case.execute(GenerateFeatureImplementationInput(feature_id=feat_id))

    # Assert
    assert output.success is True
    assert output.status == FeatureImplementationStatus.IMPLEMENTED
    error_events = [
        e for e in output.events if e.event_type == OpenCodeEventType.ERROR and "traceability" in str(e.data)
    ]
    assert len(error_events) == 1
