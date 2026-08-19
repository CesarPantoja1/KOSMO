from __future__ import annotations

import dataclasses
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from kosmo.contracts.codegen import (
    CodeRunnerPort,
    CodeWorkspace,
    FeatureImplementation,
    FeatureImplementationRepository,
    FeatureImplementationStatus,
    FileAction,
    FileOperation,
    ImplementationPlan,
    OpenCodeClientPort,
    OpenCodeEvent,
    OpenCodeEventType,
    ValidationRunResult,
    WorkspaceManagerPort,
)
from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, ImplementationId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    FeatureRepository,
    RequirementRepository,
)
from kosmo.domain.codegen.parse_validation_output import truncate_error_output
from kosmo.domain.codegen.plan_rules import validate_plan

_DEFAULT_REQ_MSG = "Esta característica no tiene requisitos EARS generados. Genera los requisitos antes de continuar."
_DEFAULT_DIAG_MSG = (
    "Esta característica no tiene diagrama de actividad generado. Genera el diagrama antes de continuar."
)


class MissingRequirementsError(ValueError):
    """Lanzada cuando la característica no tiene requisitos EARS generados (CA-02)."""

    def __init__(self, message: str = _DEFAULT_REQ_MSG) -> None:
        super().__init__(message)


class MissingDiagramError(ValueError):
    """Lanzada cuando la característica no tiene diagrama de actividad generado (CA-03)."""

    def __init__(self, message: str = _DEFAULT_DIAG_MSG) -> None:
        super().__init__(message)


@dataclass(frozen=True)
class GenerateFeatureImplementationInput:
    feature_id: FeatureId
    max_retries: int = 3
    event_sink: Callable[[OpenCodeEvent], Awaitable[None]] | None = None


@dataclass(frozen=True)
class GenerateFeatureImplementationOutput:
    success: bool
    status: FeatureImplementationStatus
    implementation: FeatureImplementation | None
    workspace: CodeWorkspace | None
    validation_result: ValidationRunResult | None = None
    generated_files: tuple[str, ...] = field(default_factory=tuple)
    error_message: str | None = None
    retry_history: tuple[tuple[str, ...], ...] = field(default_factory=tuple)
    events: tuple[OpenCodeEvent, ...] = field(default_factory=tuple)


class GenerateFeatureImplementationUseCase:
    """Caso de uso principal para orquestar la generación de código por característica."""

    def __init__(
        self,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        activity_diagram_repo: ActivityDiagramRepository,
        workspace_manager: WorkspaceManagerPort,
        opencode_client: OpenCodeClientPort,
        code_runner: CodeRunnerPort,
        implementation_repo: FeatureImplementationRepository,
    ) -> None:
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._activity_diagram_repo = activity_diagram_repo
        self._workspace_manager = workspace_manager
        self._opencode_client = opencode_client
        self._code_runner = code_runner
        self._implementation_repo = implementation_repo

    async def execute_stream(
        self,
        input_data: GenerateFeatureImplementationInput,
    ) -> AsyncIterator[OpenCodeEvent]:
        """Ejecuta el pipeline emitiendo eventos de progreso SSE en tiempo real."""
        events: list[OpenCodeEvent] = []

        async def _capture_event(ev: OpenCodeEvent) -> None:
            events.append(ev)

        output = await self._run_pipeline(input_data, event_collector=_capture_event)
        for ev in output.events:
            yield ev

    async def execute(
        self,
        input_data: GenerateFeatureImplementationInput,
    ) -> GenerateFeatureImplementationOutput:
        """Ejecuta el pipeline de implementación completo de forma síncrona."""
        return await self._run_pipeline(input_data)

    async def _run_pipeline(
        self,
        input_data: GenerateFeatureImplementationInput,
        event_collector: Callable[[OpenCodeEvent], Awaitable[None]] | None = None,
    ) -> GenerateFeatureImplementationOutput:
        # 1. Validar existencia de Feature
        feature = await self._feature_repo.by_id(input_data.feature_id)
        if feature is None:
            raise FeatureNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=f"/api/v1/features/{input_data.feature_id}/implementation",
            )

        # 2. Validar presencia de requisitos EARS (CA-02)
        req_markdown = await self._requirement_repo.by_feature_id(input_data.feature_id)
        if not req_markdown or not req_markdown.strip():
            raise MissingRequirementsError(_DEFAULT_REQ_MSG)

        # 3. Validar presencia de diagrama de actividad (CA-03)
        diagram = await self._activity_diagram_repo.by_feature_id(input_data.feature_id)
        if diagram is None or not diagram.diagram_syntax.strip():
            raise MissingDiagramError(_DEFAULT_DIAG_MSG)

        collected_events: list[OpenCodeEvent] = []

        async def _emit(event: OpenCodeEvent) -> None:
            collected_events.append(event)
            if input_data.event_sink is not None:
                await input_data.event_sink(event)
            if event_collector is not None:
                await event_collector(event)

        # 4. Adquirir lock y preparar workspace
        await self._workspace_manager.acquire_lock(feature.project_id)
        workspace: CodeWorkspace | None = None
        session_id: str | None = None

        try:
            workspace = await self._workspace_manager.ensure_workspace(feature.project_id)
            workspace_dir = workspace.workspace_dir or "/workspace"

            # Crear o cargar registro FeatureImplementation
            existing_impl = await self._implementation_repo.by_feature_id(input_data.feature_id)
            now = datetime.now(UTC)
            if existing_impl is not None:
                impl = dataclasses.replace(
                    existing_impl,
                    status=FeatureImplementationStatus.IN_PROGRESS,
                    updated_at=now,
                )
            else:
                impl = FeatureImplementation(
                    id=ImplementationId(f"impl_{feature.id}"),
                    feature_id=feature.id,
                    project_id=feature.project_id,
                    status=FeatureImplementationStatus.IN_PROGRESS,
                    max_attempts=input_data.max_retries,
                    created_at=now,
                    updated_at=now,
                )
            await self._implementation_repo.save(impl)

            # 5. Crear sesión en OpenCode
            session = await self._opencode_client.create_session(
                workspace_dir=workspace_dir,
                title=f"Feature implementation: {feature.title}",
            )
            session_id = session.session_id
            impl = dataclasses.replace(impl, session_id=session_id)
            await self._implementation_repo.save(impl)

            await _emit(
                OpenCodeEvent(
                    event_type=OpenCodeEventType.SESSION_CREATED,
                    session_id=session_id,
                    data={"workspace_dir": workspace_dir, "feature_id": str(feature.id)},
                )
            )

            # 6. Fase Plan: enviar prompt al Plan Agent
            plan_prompt = (
                f"Eres el agente de planificación para la feature '{feature.title}'.\n\n"
                f"## Descripción\n{feature.description}\n\n"
                f"## Requisitos EARS\n{req_markdown}\n\n"
                f"## Diagrama de Actividad\n{diagram.diagram_syntax}\n\n"
                "Propón un plan de implementación detallando los archivos a crear y modificar."
            )

            plan_operations: list[FileOperation] = []
            async for ev in self._opencode_client.send_prompt(session_id, plan_prompt, agent="plan"):
                await _emit(ev)
                if ev.event_type == OpenCodeEventType.PLAN_COMPLETE:
                    ops_raw: object = ev.data.get("operations")
                    if isinstance(ops_raw, list):
                        ops_items: list[object] = list(ops_raw)  # type: ignore[reportUnknownVariableType]
                        for op_item in ops_items:
                            if isinstance(op_item, dict):
                                op_dict: dict[object, object] = dict(op_item)  # type: ignore[reportUnknownVariableType]
                                action_raw = op_dict.get("action", "create")
                                action_val = str(action_raw).lower() if action_raw is not None else "create"
                                action = FileAction.CREATE if action_val == "create" else FileAction.MODIFY
                                path_val = str(op_dict.get("path", ""))
                                desc_val = str(op_dict.get("description", ""))
                                plan_operations.append(
                                    FileOperation(
                                        path=path_val,
                                        action=action,
                                        description=desc_val,
                                    )
                                )

            if not plan_operations:
                plan_operations.append(
                    FileOperation(path=f"src/{feature.slug}.ts", action=FileAction.CREATE),
                )
                plan_operations.append(
                    FileOperation(path=f"tests/{feature.slug}.test.ts", action=FileAction.CREATE),
                )

            impl_plan = ImplementationPlan(
                feature_id=feature.id,
                operations=tuple(plan_operations),
                summary=f"Plan para {feature.title}",
                created_at=datetime.now(UTC),
            )
            # Validar plan determinísticamente
            validate_plan(impl_plan, workspace.manifest_files, workspace_dir)
            impl = dataclasses.replace(impl, plan=impl_plan)
            await self._implementation_repo.save(impl)

            # 7. Fase Build: enviar prompt al Build Agent
            plan_lines = "\n".join(
                f"- [{op.action}] {op.path}" + (f" — {op.description}" if op.description else "")
                for op in impl_plan.operations
            )
            build_prompt = (
                f"Eres el agente de construcción para la feature '{feature.title}'.\n\n"
                f"## Plan aprobado\n{plan_lines}\n\n"
                f"## Requisitos EARS\n{req_markdown}\n\n"
                "Implementa el código y las pruebas respetando el plan aprobado."
            )

            generated_files: set[str] = set()
            async for ev in self._opencode_client.send_prompt(session_id, build_prompt, agent="build"):
                await _emit(ev)
                if ev.event_type == OpenCodeEventType.FILE_EDIT:
                    file_path: object = ev.data.get("path")
                    if file_path is not None:
                        generated_files.add(str(file_path))
                elif ev.event_type == OpenCodeEventType.BUILD_COMPLETE:
                    files_obj: object = ev.data.get("files")
                    if isinstance(files_obj, list):
                        files_items: list[object] = list(files_obj)  # type: ignore[reportUnknownVariableType]
                        for f_item in files_items:
                            generated_files.add(str(f_item))

            if not generated_files:
                for op in plan_operations:
                    generated_files.add(op.path)

            # 8. Fase Validación & Reintentos (hasta max_retries)
            attempt = 0
            validation_result: ValidationRunResult | None = None
            retry_history: list[tuple[str, ...]] = []

            while attempt < input_data.max_retries:
                attempt += 1
                validation_result = await self._code_runner.run_pipeline(workspace_dir)
                impl = dataclasses.replace(
                    impl,
                    attempt_count=attempt,
                    last_validation=validation_result,
                    generated_files=tuple(sorted(generated_files)),
                    updated_at=datetime.now(UTC),
                )
                await self._implementation_repo.save(impl)

                if validation_result.all_passed:
                    break

                # Acumular historial de errores del intento actual
                retry_history.append(validation_result.error_summary)

                if attempt < input_data.max_retries:
                    error_feedback = truncate_error_output(
                        "\n".join(validation_result.error_summary),
                        max_chars=2000,
                    )

                    # Emitir evento RETRY para notificar al frontend
                    await _emit(
                        OpenCodeEvent(
                            event_type=OpenCodeEventType.RETRY,
                            session_id=session_id,
                            data={
                                "attempt": attempt,
                                "max_retries": input_data.max_retries,
                                "error_summary": list(validation_result.error_summary),
                            },
                        )
                    )

                    fix_prompt = (
                        f"La validación falló en el intento {attempt}/{input_data.max_retries}.\n"
                        f"## Errores detectados:\n{error_feedback}\n\n"
                        "Corrige los archivos necesarios para resolver estos errores."
                    )
                    async for ev in self._opencode_client.send_prompt(session_id, fix_prompt, agent="build"):
                        await _emit(ev)
                        if ev.event_type == OpenCodeEventType.FILE_EDIT:
                            file_path_fix: object = ev.data.get("path")
                            if file_path_fix is not None:
                                generated_files.add(str(file_path_fix))

            # 9. Conclusión del pipeline
            if validation_result is not None and validation_result.all_passed:
                await self._workspace_manager.commit_workspace(
                    feature.project_id,
                    f"feat({feature.slug}): implement feature {feature.display_id} - {feature.title}",
                )
                impl = dataclasses.replace(
                    impl,
                    status=FeatureImplementationStatus.IMPLEMENTED,
                    generated_files=tuple(sorted(generated_files)),
                    updated_at=datetime.now(UTC),
                )
                await self._implementation_repo.save(impl)
                await self._opencode_client.close_session(session_id)

                done_event = OpenCodeEvent(
                    event_type=OpenCodeEventType.DONE,
                    session_id=session_id,
                    data={"status": "implemented", "generated_files": list(generated_files)},
                )
                await _emit(done_event)

                return GenerateFeatureImplementationOutput(
                    success=True,
                    status=FeatureImplementationStatus.IMPLEMENTED,
                    implementation=impl,
                    workspace=workspace,
                    validation_result=validation_result,
                    generated_files=tuple(sorted(generated_files)),
                    retry_history=tuple(retry_history),
                    events=tuple(collected_events),
                )
            else:
                # CA-04: Reintentos agotados -> rollback + REQUIRES_REVIEW
                await self._workspace_manager.rollback_workspace(feature.project_id)

                # Construir mensaje de error con historial
                history_lines: list[str] = []
                for idx, errors in enumerate(retry_history, 1):
                    history_lines.append(f"Intento {idx}: {'; '.join(errors)}")
                error_detail = "\n".join(history_lines) if history_lines else "Sin detalles"

                impl = dataclasses.replace(
                    impl,
                    status=FeatureImplementationStatus.REQUIRES_REVIEW,
                    generated_files=tuple(sorted(generated_files)),
                    retry_history=tuple(retry_history),
                    updated_at=datetime.now(UTC),
                )
                await self._implementation_repo.save(impl)
                await self._opencode_client.close_session(session_id)

                error_event = OpenCodeEvent(
                    event_type=OpenCodeEventType.ERROR,
                    session_id=session_id,
                    data={
                        "error": "Validación fallida tras agotar reintentos",
                        "status": "requires_review",
                        "retry_history": [list(errs) for errs in retry_history],
                    },
                )
                await _emit(error_event)

                return GenerateFeatureImplementationOutput(
                    success=False,
                    status=FeatureImplementationStatus.REQUIRES_REVIEW,
                    implementation=impl,
                    workspace=workspace,
                    validation_result=validation_result,
                    generated_files=tuple(sorted(generated_files)),
                    error_message=(
                        f"Validación fallida tras agotar {input_data.max_retries} reintentos de corrección.\n"
                        f"{error_detail}"
                    ),
                    retry_history=tuple(retry_history),
                    events=tuple(collected_events),
                )

        finally:
            await self._workspace_manager.release_lock(feature.project_id)
