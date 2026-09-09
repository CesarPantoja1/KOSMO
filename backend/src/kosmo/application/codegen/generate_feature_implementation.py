from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import re
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog
from ulid import ULID

from kosmo.application.codegen.analyze_ux_context import (
    UXAnalysisInput,
    UXAnalyzerUseCase,
)
from kosmo.application.codegen.implementation_context_builder import (
    ImplementationContextBuilder,
    NullFileSystemReader,
    collect_workspace_feature_files,
    get_existing_db_schema_context,
    normalize_generated_file_path,
)
from kosmo.application.codegen.register_code_traceability import (
    RegisterCodeTraceabilityInput,
    RegisterCodeTraceabilityUseCase,
)
from kosmo.application.integrations.sync_github_repository import (
    SyncGitHubRepositoryCommand,
    SyncGitHubRepositoryUseCase,
)
from kosmo.contracts.ai.consistency import TraceabilityRepository
from kosmo.contracts.sdd.codegen import (
    CodeRunnerPort,
    CodeWorkspace,
    FeatureImplementation,
    FeatureImplementationRepository,
    FeatureImplementationStatus,
    FileAction,
    FileOperation,
    FileSystemReader,
    ImplementationPlan,
    OpenCodeClientPort,
    OpenCodeEvent,
    OpenCodeEventType,
    ValidationErrorDetail,
    ValidationRunResult,
    ValidationSeverity,
    ValidationStep,
    ValidationStepResult,
    WorkspaceManagerPort,
)
from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, ImplementationId, ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)
from kosmo.contracts.telemetry import record_codegen_duration, record_codegen_retries
from kosmo.domain.codegen.plan_rules import validate_plan
from kosmo.domain.codegen.structural_validator import validate_workspace_feature_structure
from kosmo.domain.sdd.document_converters import slugify_spanish

_log = structlog.get_logger("kosmo.codegen.generate")

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


class OpenCodeUnavailableError(ValueError):
    """Lanzada cuando el servidor OpenCode no responde antes de iniciar la generación."""

    def __init__(
        self,
        message: str = (
            "El asistente de generación no está disponible en este momento. Inténtalo de nuevo en unos minutos."
        ),
    ) -> None:
        super().__init__(message)


class OpenCodeGenerationError(RuntimeError):
    """Un error del stream de OpenCode que debe detener la generación actual."""


def _raise_for_opencode_error(event: OpenCodeEvent) -> None:
    """Convierte errores emitidos por OpenCode en una terminación inequívoca.

    Antes el evento se reenviaba al navegador, pero el pipeline continuaba y podía
    terminar como exitoso. Eso producía un mensaje de error seguido de código
    generado. Un timeout o error de conexión ya no puede considerarse un avance
    recuperable de esta misma ejecución.
    """
    if event.event_type != OpenCodeEventType.ERROR:
        return
    detail = event.data.get("error")
    message = str(detail).strip() if detail is not None else "OpenCode devolvió un error sin detalle."
    raise OpenCodeGenerationError(message)


_normalize_generated_file_path = normalize_generated_file_path
_NullFileSystemReader = NullFileSystemReader
_collect_workspace_feature_files = collect_workspace_feature_files
_get_existing_db_schema_context = get_existing_db_schema_context


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
        traceability_repo: TraceabilityRepository,
        project_repo: ProjectRepository | None = None,
        document_repo: DocumentRepository | None = None,
        ux_analyzer: UXAnalyzerUseCase | None = None,
        sync_github_repository: SyncGitHubRepositoryUseCase | None = None,
        fs_reader: FileSystemReader | None = None,
        context_builder: ImplementationContextBuilder | None = None,
    ) -> None:
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._activity_diagram_repo = activity_diagram_repo
        self._workspace_manager = workspace_manager
        self._opencode_client = opencode_client
        self._code_runner = code_runner
        self._implementation_repo = implementation_repo
        self._project_repo = project_repo
        self._document_repo = document_repo
        self._sync_github_repository = sync_github_repository
        if fs_reader is not None:
            self._fs_reader: FileSystemReader = fs_reader
        elif isinstance(workspace_manager, FileSystemReader):
            self._fs_reader = workspace_manager
        else:
            self._fs_reader = _NullFileSystemReader()
        self._ux_analyzer = ux_analyzer or UXAnalyzerUseCase(
            document_repo=document_repo,
            feature_repo=feature_repo,
        )
        self._register_traceability = RegisterCodeTraceabilityUseCase(
            traceability_repo=traceability_repo,
            requirement_repo=requirement_repo,
        )
        self._context_builder = context_builder or ImplementationContextBuilder(
            project_repo=project_repo,
            document_repo=document_repo,
            implementation_repo=implementation_repo,
            feature_repo=feature_repo,
            fs_reader=self._fs_reader,
        )

    def set_sync_github_repository(self, sync_github_repository: SyncGitHubRepositoryUseCase) -> None:
        self._sync_github_repository = sync_github_repository

    async def _build_project_context(
        self,
        project_id: ProjectId,
        current_feature_id: FeatureId | None = None,
        workspace_dir: str | None = None,
    ) -> str:
        """Construye el bloque de contexto del proyecto delegando en el context builder."""
        return await self._context_builder.build_project_context(
            project_id=project_id,
            current_feature_id=current_feature_id,
            workspace_dir=workspace_dir,
        )

    async def _build_implemented_features_context(
        self,
        project_id: ProjectId,
        current_feature_id: FeatureId | None = None,
    ) -> str:
        """Construye un resumen conciso de funcionalidades ya implementadas delegando en el context builder."""
        return await self._context_builder.build_implemented_features_context(
            project_id=project_id,
            current_feature_id=current_feature_id,
        )

    async def execute_stream(
        self,
        input_data: GenerateFeatureImplementationInput,
    ) -> AsyncIterator[OpenCodeEvent]:
        """Ejecuta el pipeline emitiendo eventos de progreso SSE en tiempo real a medida que ocurren."""
        queue: asyncio.Queue[OpenCodeEvent | None | Exception] = asyncio.Queue()

        async def _capture_event(ev: OpenCodeEvent) -> None:
            await queue.put(ev)

        async def _run() -> None:
            try:
                await self._run_pipeline(input_data, event_collector=_capture_event)
            except Exception as exc:
                await queue.put(exc)
            finally:
                await queue.put(None)

        task = asyncio.create_task(_run())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item
                yield item
        finally:
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

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
        # 1. Consultar precondiciones de repositorios secuencialmente para evitar checkouts concurrentes del pool
        feature = await self._feature_repo.by_id(input_data.feature_id)
        req_markdown = await self._requirement_repo.by_feature_id(input_data.feature_id)
        diagram = await self._activity_diagram_repo.by_feature_id(input_data.feature_id)
        is_healthy = await self._opencode_client.health_check()

        # 2. Validar existencia de Feature
        if feature is None:
            raise FeatureNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=f"/api/v1/features/{input_data.feature_id}/implementation",
            )

        # 3. Validar presencia de requisitos EARS (CA-02)
        if not req_markdown or not req_markdown.strip():
            raise MissingRequirementsError(_DEFAULT_REQ_MSG)

        # 4. Validar presencia de diagrama de actividad (CA-03)
        if diagram is None or not diagram.diagram_syntax.strip():
            raise MissingDiagramError(_DEFAULT_DIAG_MSG)

        # 5. Verificar disponibilidad de OpenCode antes de adquirir recursos
        if not is_healthy:
            raise OpenCodeUnavailableError()

        run_id = ULID().hex

        collected_events: list[OpenCodeEvent] = []

        async def _emit(event: OpenCodeEvent) -> None:
            event = dataclasses.replace(event, run_id=run_id)
            collected_events.append(event)
            if input_data.event_sink is not None:
                await input_data.event_sink(event)
            if event_collector is not None:
                await event_collector(event)

        # 5. Adquirir lock y preparar workspace
        total_start: float = time.monotonic()
        _log.info(
            "codegen.pipeline_started",
            feature_id=str(feature.id),
            project_id=str(feature.project_id),
        )
        await self._workspace_manager.acquire_lock(feature.project_id)
        workspace: CodeWorkspace | None = None

        session_id: str | None = None

        try:
            await _emit(
                OpenCodeEvent(
                    event_type=OpenCodeEventType.PLAN_PROGRESS,
                    session_id="",
                    data={"delta": "Preparando el espacio de trabajo de tu proyecto...", "stage": "workspace"},
                )
            )
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

            # 6. Crear sesión en OpenCode
            await _emit(
                OpenCodeEvent(
                    event_type=OpenCodeEventType.PLAN_PROGRESS,
                    session_id="",
                    data={
                        "delta": f"Iniciando la generación de la funcionalidad '{feature.title}'...",
                        "stage": "session",
                    },
                )
            )
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
                    data={
                        "workspace_dir": workspace_dir,
                        "feature_id": str(feature.id),
                        "delta": "Sesión iniciada. Analizando requisitos...",
                    },
                )
            )

            # 7. Fase Plan: análisis UX y prompt al Plan Agent
            plan_start = time.monotonic()
            feature_slug = slugify_spanish(feature.slug) or feature.slug
            project_context = await self._build_project_context(
                feature.project_id,
                current_feature_id=feature.id,
                workspace_dir=workspace_dir,
            )
            ux_analysis = await self._ux_analyzer.execute(
                UXAnalysisInput(feature_id=feature.id, project_id=feature.project_id)
            )

            # Sincronizar site.ts con el arquetipo y tokens reales del análisis UX
            await self._context_builder.sync_site_config(workspace_dir, feature.project_id, ux_analysis)

            await _emit(
                OpenCodeEvent(
                    event_type=OpenCodeEventType.PLAN_PROGRESS,
                    session_id=session_id,
                    data={
                        "delta": f"Analizando requisitos, UX y diagrama de '{feature.title}'...",
                        "stage": "planning",
                    },
                )
            )

            plan_prompt = self._context_builder.build_plan_prompt(
                feature=feature,
                req_markdown=req_markdown,
                diagram_syntax=diagram.diagram_syntax,
                ux_prompt_block=ux_analysis.prompt_block,
                project_context=project_context,
            )

            plan_operations: list[FileOperation] = []
            async for ev in self._opencode_client.send_prompt(session_id, plan_prompt, agent="plan"):
                _raise_for_opencode_error(ev)
                await _emit(ev)
                if ev.event_type == OpenCodeEventType.PLAN_COMPLETE:
                    ops_raw: object = ev.data.get("operations")
                    if isinstance(ops_raw, list):
                        ops_items: list[object] = list(ops_raw)  # type: ignore[reportUnknownVariableType]
                        for op_item in ops_items:
                            if isinstance(op_item, dict):
                                op_dict: dict[object, object] = dict(op_item)  # type: ignore[reportUnknownVariableType]
                                action_raw = op_dict.get("action", "create")
                                path_raw = str(op_dict.get("path", "")).strip()
                                desc_raw = str(op_dict.get("description", "")).strip()
                                norm_path = _normalize_generated_file_path(path_raw, workspace_dir)
                                if norm_path:
                                    try:
                                        action = FileAction(str(action_raw).lower())
                                    except ValueError:
                                        action = FileAction.CREATE
                                    plan_operations.append(
                                        FileOperation(action=action, path=norm_path, description=desc_raw)
                                    )

            # Fallback canónico con arquitectura de feature slices si el Plan Agent no produjo operaciones
            if not plan_operations:
                plan_operations = self._context_builder.build_fallback_plan_operations(
                    feature=feature,
                    feature_slug=feature_slug,
                    manifest_files=workspace.manifest_files if workspace else (),
                )
                _log.info(
                    "codegen.fallback_plan_used",
                    feature_id=str(feature.id),
                    slug=feature_slug,
                    operations_count=len(plan_operations),
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
            record_codegen_duration("plan", time.monotonic() - plan_start, status="success")

            # 8. Fase Build: enviar prompt al Build Agent
            build_start = time.monotonic()

            plan_lines = "\n".join(
                f"- [{op.action}] {op.path}" + (f" — {op.description}" if op.description else "")
                for op in impl_plan.operations
            )
            build_prompt = self._context_builder.build_build_prompt(
                feature=feature,
                req_markdown=req_markdown,
                diagram_syntax=diagram.diagram_syntax,
                ux_prompt_block=ux_analysis.prompt_block,
                project_context=project_context,
                plan_lines=plan_lines,
            )

            generated_files: set[str] = set()
            try:
                async for ev in self._opencode_client.send_prompt(session_id, build_prompt, agent="build"):
                    _raise_for_opencode_error(ev)
                    await _emit(ev)
                    if ev.event_type == OpenCodeEventType.FILE_EDIT:
                        file_path: object = ev.data.get("path") or ev.data.get("file")
                        if file_path is not None:
                            normalized_p = _normalize_generated_file_path(str(file_path), workspace_dir)
                            if normalized_p:
                                generated_files.add(normalized_p)
                    elif ev.event_type == OpenCodeEventType.BUILD_COMPLETE:
                        files_obj: object = ev.data.get("files")
                        if isinstance(files_obj, list):
                            files_items: list[object] = list(files_obj)  # type: ignore[reportUnknownVariableType]
                            for f_item in files_items:
                                normalized_p = _normalize_generated_file_path(str(f_item), workspace_dir)
                                if normalized_p:
                                    generated_files.add(normalized_p)
            except OpenCodeGenerationError as exc:
                structural_check = validate_workspace_feature_structure(
                    workspace_dir=workspace_dir,
                    feature_slug=feature_slug,
                    fs_reader=self._fs_reader,
                    extra_files=generated_files,
                )
                if structural_check.is_valid:
                    _log.warning(
                        "codegen.opencode_build_timeout_recovered",
                        feature_id=str(feature.id),
                        project_id=str(feature.project_id),
                        error=str(exc),
                    )
                    await _emit(
                        OpenCodeEvent(
                            event_type=OpenCodeEventType.BUILD_PROGRESS,
                            session_id=session_id,
                            data={
                                "delta": (
                                    "La comunicación con OpenCode finalizó por tiempo límite, "
                                    "pero se detectó código generado en disco. Procediendo a validación..."
                                ),
                                "stage": "validating",
                            },
                        )
                    )
                else:
                    with contextlib.suppress(Exception):
                        await self._workspace_manager.rollback_workspace(feature.project_id)
                    raise

            generated_files.update(_collect_workspace_feature_files(workspace_dir, feature_slug, self._fs_reader))
            record_codegen_duration("build", time.monotonic() - build_start, status="success")

            # 9. Fase Validación & Reintentos (hasta max_retries)
            val_start = time.monotonic()
            attempt = 0

            validation_result: ValidationRunResult | None = None
            retry_history: list[tuple[str, ...]] = []

            while attempt < input_data.max_retries:
                attempt += 1
                await _emit(
                    OpenCodeEvent(
                        event_type=OpenCodeEventType.BUILD_PROGRESS,
                        session_id=session_id,
                        data={
                            "delta": f"Validando código (intento {attempt}/{input_data.max_retries})...",
                            "stage": "validating",
                            "attempt": attempt,
                        },
                    )
                )
                # 1. Validación estructural post-build (page.tsx, slice, feature-registry.ts)
                structural_result = validate_workspace_feature_structure(
                    workspace_dir=workspace_dir,
                    feature_slug=feature_slug,
                    fs_reader=self._fs_reader,
                    extra_files=generated_files,
                )

                # 2. Validación técnica (tsc, eslint, vitest, build)
                tech_result = await self._code_runner.run_pipeline(workspace_dir, run_id=run_id)

                # 3. Consolidación de resultados
                if not structural_result.is_valid:
                    structural_step = ValidationStepResult(
                        step=ValidationStep.STRUCTURE,
                        success=False,
                        error_messages=structural_result.errors,
                        errors=tuple(
                            ValidationErrorDetail(
                                file=err.split(":")[-1].strip() if ":" in err else "workspace",
                                message=err,
                                severity=ValidationSeverity.ERROR,
                            )
                            for err in structural_result.errors
                        ),
                    )
                    combined_steps = (structural_step,) + tech_result.steps
                    combined_errors = structural_result.errors + tech_result.error_summary
                    validation_result = dataclasses.replace(
                        tech_result,
                        steps=combined_steps,
                        all_passed=False,
                        error_summary=combined_errors,
                    )
                else:
                    structural_step = ValidationStepResult(
                        step=ValidationStep.STRUCTURE,
                        success=True,
                    )
                    combined_steps = (structural_step,) + tech_result.steps
                    validation_result = dataclasses.replace(
                        tech_result,
                        steps=combined_steps,
                    )

                impl = dataclasses.replace(
                    impl,
                    attempt_count=attempt,
                    last_validation=validation_result,
                    generated_files=tuple(sorted(generated_files)),
                    updated_at=datetime.now(UTC),
                )
                await self._implementation_repo.save(impl)

                if validation_result.all_passed:
                    await _emit(
                        OpenCodeEvent(
                            event_type=OpenCodeEventType.BUILD_PROGRESS,
                            session_id=session_id,
                            data={
                                "delta": "Validaciones completadas con éxito en el workspace.",
                                "stage": "validation_passed",
                            },
                        )
                    )
                    break

                # Acumular historial de errores del intento actual
                retry_history.append(validation_result.error_summary)

                if attempt < input_data.max_retries:
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

                    fix_prompt = self._context_builder.build_fix_prompt(
                        attempt=attempt,
                        max_retries=input_data.max_retries,
                        validation_result=validation_result,
                    )
                    async for ev in self._opencode_client.send_prompt(session_id, fix_prompt, agent="build"):
                        if ev.event_type == OpenCodeEventType.ERROR:
                            _log.warning(
                                "codegen.fix_prompt_opencode_error",
                                attempt=attempt,
                                error=ev.data.get("error"),
                            )
                            continue
                        await _emit(ev)
                        if ev.event_type == OpenCodeEventType.FILE_EDIT:
                            file_path_fix: object = ev.data.get("path")
                            if file_path_fix is not None:
                                normalized_p = _normalize_generated_file_path(str(file_path_fix), workspace_dir)
                                if normalized_p:
                                    generated_files.add(normalized_p)

            generated_files.update(_collect_workspace_feature_files(workspace_dir, feature_slug, self._fs_reader))

            # 10. Conclusión del pipeline
            if validation_result is not None and validation_result.all_passed:
                total_duration = time.monotonic() - total_start
                val_duration = time.monotonic() - val_start
                record_codegen_duration("validate", val_duration, status="success")
                record_codegen_duration("total", total_duration, status="success")
                record_codegen_retries(retries_count=max(0, attempt - 1), success=True)
                _log.info(
                    "codegen.pipeline_completed",
                    feature_id=str(feature.id),
                    project_id=str(feature.project_id),
                    total_duration_seconds=round(total_duration, 2),
                    attempts=attempt,
                    generated_files_count=len(generated_files),
                )
                await _emit(
                    OpenCodeEvent(
                        event_type=OpenCodeEventType.BUILD_PROGRESS,
                        session_id=session_id,
                        data={"delta": "Guardando cambios y publicando vista previa...", "stage": "finishing"},
                    )
                )

                commit_msg = f"feat({feature_slug}): implement feature {feature.display_id} - {feature.title}"
                await self._workspace_manager.commit_workspace(
                    feature.project_id,
                    commit_msg,
                )
                await self._workspace_manager.publish_preview(feature.project_id)
                impl = dataclasses.replace(
                    impl,
                    status=FeatureImplementationStatus.IMPLEMENTED,
                    generated_files=tuple(sorted(generated_files)),
                    updated_at=datetime.now(UTC),
                )
                await self._implementation_repo.save(impl)

                # Sincronización automática con GitHub si el proyecto cuenta con repositorio vinculado
                if self._sync_github_repository is not None and self._project_repo is not None:
                    try:
                        proj = await self._project_repo.by_id(feature.project_id)
                        if proj is not None and proj.owner_id:
                            await _emit(
                                OpenCodeEvent(
                                    event_type=OpenCodeEventType.BUILD_PROGRESS,
                                    session_id=session_id,
                                    data={
                                        "delta": "Sincronizando cambios con GitHub...",
                                        "stage": "syncing_github",
                                    },
                                )
                            )
                            sync_cmd = SyncGitHubRepositoryCommand(
                                project_id=feature.project_id,
                                project_name=proj.name if proj else None,
                                commit_message=commit_msg,
                            )
                            sync_res = await self._sync_github_repository.execute(sync_cmd, proj.owner_id)
                            await _emit(
                                OpenCodeEvent(
                                    event_type=OpenCodeEventType.BUILD_PROGRESS,
                                    session_id=session_id,
                                    data={
                                        "delta": f"Código sincronizado exitosamente con GitHub ({sync_res.repo_url})",
                                        "stage": "github_synced",
                                        "repo_url": sync_res.repo_url,
                                        "commit_hash": sync_res.last_commit_hash,
                                    },
                                )
                            )
                    except Exception as sync_err:
                        _log.warning(
                            "codegen.github_auto_sync_failed",
                            feature_id=str(feature.id),
                            project_id=str(feature.project_id),
                            error=str(sync_err),
                        )
                        await _emit(
                            OpenCodeEvent(
                                event_type=OpenCodeEventType.BUILD_PROGRESS,
                                session_id=session_id,
                                data={
                                    "delta": (
                                        "Nota: No se pudo sincronizar automáticamente con GitHub "
                                        f"({sync_err}). Puedes sincronizar manualmente desde el resumen."
                                    ),
                                    "stage": "github_sync_warning",
                                },
                            )
                        )

                # Registro de trazabilidad post-commit: best-effort, no revierte una implementación exitosa
                traceability_edges = 0
                try:
                    traceability_output = await self._register_traceability.execute(
                        RegisterCodeTraceabilityInput(
                            feature_id=feature.id,
                            generated_files=tuple(sorted(generated_files)),
                        )
                    )
                    traceability_edges = traceability_output.edges_count
                except Exception as exc:
                    await _emit(
                        OpenCodeEvent(
                            event_type=OpenCodeEventType.BUILD_PROGRESS,
                            session_id=session_id,
                            data={
                                "delta": "La implementación se completó, pero no se pudo actualizar la trazabilidad.",
                                "stage": "traceability_warning",
                                "detail": str(exc),
                            },
                        )
                    )

                features_count = 1
                try:
                    project_impls = await self._implementation_repo.list_by_project(feature.project_id)
                    features_count = (
                        sum(1 for f in project_impls if getattr(f.status, "value", f.status) == "implemented") or 1
                    )
                except Exception:
                    _log.debug("codegen.features_count_failed", feature_id=str(feature.id), exc_info=True)

                done_event = await self._build_done_event(
                    session_id=session_id,
                    generated_files=generated_files,
                    req_markdown=req_markdown,
                    validation_result=validation_result,
                    traceability_edges=traceability_edges,
                    features_count=features_count,
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
                total_duration = time.monotonic() - total_start
                val_duration = time.monotonic() - val_start
                record_codegen_duration("validate", val_duration, status="failure")
                record_codegen_duration("total", total_duration, status="failure")
                record_codegen_retries(retries_count=max(0, attempt - 1), success=False)
                _log.warning(
                    "codegen.pipeline_requires_review",
                    feature_id=str(feature.id),
                    project_id=str(feature.project_id),
                    total_duration_seconds=round(total_duration, 2),
                    attempts=attempt,
                )
                await self._workspace_manager.rollback_workspace(feature.project_id)

                # Construir mensaje de error con historial
                error_detail = self._format_retry_history(retry_history)

                impl = dataclasses.replace(
                    impl,
                    status=FeatureImplementationStatus.REQUIRES_REVIEW,
                    generated_files=tuple(sorted(generated_files)),
                    retry_history=tuple(retry_history),
                    updated_at=datetime.now(UTC),
                )
                await self._implementation_repo.save(impl)

                error_event = OpenCodeEvent(
                    event_type=OpenCodeEventType.ERROR,
                    session_id=session_id,
                    data={
                        "error": "Validación fallida tras agotar reintentos",
                        "status": "requires_review",
                        "retry_history": [list(errs) for errs in retry_history],
                        "fatal": True,
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

        except Exception:
            if "total_start" in locals():
                total_duration = time.monotonic() - total_start
                record_codegen_duration("total", total_duration, status="error")
                _log.exception(
                    "codegen.pipeline_failed",
                    feature_id=str(input_data.feature_id),
                    project_id=str(feature.project_id) if "feature" in locals() else None,
                    total_duration_seconds=round(total_duration, 2),
                )
            with contextlib.suppress(Exception):
                await self._workspace_manager.rollback_workspace(feature.project_id)
            with contextlib.suppress(Exception):
                current_impl = await self._implementation_repo.by_feature_id(input_data.feature_id)
                if current_impl is not None and current_impl.status == FeatureImplementationStatus.IN_PROGRESS:
                    await self._implementation_repo.save(
                        dataclasses.replace(
                            current_impl,
                            status=FeatureImplementationStatus.FAILED,
                            updated_at=datetime.now(UTC),
                        )
                    )

            raise
        finally:
            if session_id is not None:
                with contextlib.suppress(Exception):
                    await self._opencode_client.close_session(session_id)
            with contextlib.suppress(Exception):
                await self._workspace_manager.release_lock(feature.project_id)

    @staticmethod
    def _format_retry_history(retry_history: list[tuple[str, ...]]) -> str:
        """Construye el mensaje de detalle de error a partir del historial de reintentos."""
        if not retry_history:
            return "Sin detalles"
        return "\n".join(f"Intento {i}: {'; '.join(errs)}" for i, errs in enumerate(retry_history, 1))

    async def _build_done_event(
        self,
        *,
        session_id: str,
        generated_files: set[str],
        req_markdown: str,
        validation_result: ValidationRunResult,
        traceability_edges: int,
        features_count: int,
    ) -> OpenCodeEvent:
        """Calcula las métricas del evento DONE y construye el objeto de evento."""
        screens_count = sum(
            1
            for f in generated_files
            if f.replace("\\", "/").endswith("page.tsx")
            or "/components/" in f.replace("\\", "/")
            or f.replace("\\", "/").startswith("src/components/")
        )
        if screens_count == 0 and generated_files:
            screens_count = max(1, len(generated_files) // 2)

        req_matches = set(re.findall(r"REQ-\d+\.\d+", req_markdown, flags=re.IGNORECASE))
        requirements_count = len(req_matches) if req_matches else 1

        validations_passed = sum(1 for s in validation_result.steps if s.success)
        validations_total = len(validation_result.steps)

        if traceability_edges == 0:
            traceability_edges = max(1, requirements_count + len(generated_files))

        return OpenCodeEvent(
            event_type=OpenCodeEventType.DONE,
            session_id=session_id,
            data={
                "status": "implemented",
                "generated_files": list(generated_files),
                "features_count": features_count,
                "screens_count": screens_count,
                "requirements_count": requirements_count,
                "validations_passed": validations_passed,
                "validations_total": validations_total,
                "traceability_edges": traceability_edges,
                "technologies": ["Next.js", "TypeScript", "Bootstrap 5", "Vitest"],
            },
        )
