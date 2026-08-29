from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ulid import ULID

from kosmo.application.codegen.analyze_ux_context import (
    UXAnalysisInput,
    UXAnalyzerUseCase,
)
from kosmo.application.codegen.register_code_traceability import (
    RegisterCodeTraceabilityInput,
    RegisterCodeTraceabilityUseCase,
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
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ImplementationId, ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)
from kosmo.domain.codegen.parse_validation_output import truncate_error_output
from kosmo.domain.codegen.plan_rules import validate_plan
from kosmo.domain.codegen.site_config import format_site_config
from kosmo.domain.codegen.structural_validator import validate_workspace_feature_structure
from kosmo.domain.sdd.document_converters import document_to_markdown

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
        self._ux_analyzer = ux_analyzer or UXAnalyzerUseCase(
            document_repo=document_repo,
            feature_repo=feature_repo,
        )
        self._register_traceability = RegisterCodeTraceabilityUseCase(
            traceability_repo=traceability_repo,
            requirement_repo=requirement_repo,
        )

    async def _build_project_context(
        self,
        project_id: ProjectId,
        current_feature_id: FeatureId | None = None,
    ) -> str:
        """Construye el bloque de contexto del proyecto (nombre, descripción, visión y features previas)."""
        lines: list[str] = ["## Contexto del proyecto"]
        if self._project_repo is not None:
            project = await self._project_repo.by_id(project_id)
            if project is not None:
                lines.append(f"- Nombre: {project.name}")
                if project.description:
                    lines.append(f"- Descripción: {project.description}")

        if self._document_repo is not None:
            discovery = await self._document_repo.get_discovery(project_id)
            if discovery is not None:
                try:
                    vision = document_to_markdown(discovery)
                except Exception:
                    vision = ""
                if vision:
                    lines.append(f"\n### Visión del producto (descubrimiento)\n{vision}")

        # Contexto inter-feature: funcionalidades ya implementadas
        implemented_context = await self._build_implemented_features_context(
            project_id=project_id,
            current_feature_id=current_feature_id,
        )
        if implemented_context:
            lines.append(f"\n### Funcionalidades ya implementadas en el proyecto\n{implemented_context}")

        return "\n".join(lines)

    async def _build_implemented_features_context(
        self,
        project_id: ProjectId,
        current_feature_id: FeatureId | None = None,
    ) -> str:
        """Construye un resumen conciso de funcionalidades ya implementadas para evitar duplicación."""
        try:
            implementations = await self._implementation_repo.list_by_project(project_id)
        except Exception:
            return ""

        implemented_impls = [
            impl
            for impl in implementations
            if impl.status == FeatureImplementationStatus.IMPLEMENTED
            and (current_feature_id is None or impl.feature_id != current_feature_id)
        ]
        if not implemented_impls:
            return ""

        feature_map: dict[str, Feature] = {}
        try:
            features = await self._feature_repo.list_by_project(project_id)
            feature_map = {str(f.id): f for f in features}
        except Exception:
            feature_map = {}

        lines: list[str] = []
        for impl in implemented_impls:
            feat = feature_map.get(str(impl.feature_id))
            title = feat.title if feat else str(impl.feature_id)
            slug = feat.slug if feat else ""
            slug_info = f" (slug: `{slug}`)" if slug else ""
            files_preview = ", ".join(f"`{f}`" for f in impl.generated_files[:4])
            if len(impl.generated_files) > 4:
                files_preview += f" (+{len(impl.generated_files) - 4} archivos)"
            files_info = f" — Archivos: {files_preview}" if impl.generated_files else ""
            lines.append(f"- **{title}**{slug_info}{files_info}")

        return "\n".join(lines)

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

        # 4. Verificar disponibilidad de OpenCode antes de adquirir recursos
        if not await self._opencode_client.health_check():
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
            project_context = await self._build_project_context(
                feature.project_id,
                current_feature_id=feature.id,
            )
            ux_analysis = await self._ux_analyzer.execute(
                UXAnalysisInput(feature_id=feature.id, project_id=feature.project_id)
            )

            # Sincronizar site.ts con el arquetipo y tokens reales del análisis UX
            site_file = Path(workspace_dir) / "src" / "lib" / "site.ts"
            if site_file.exists() and self._project_repo:
                with contextlib.suppress(Exception):
                    proj = await self._project_repo.by_id(feature.project_id)
                    p_name = proj.name if proj and proj.name else "KOSMO App"
                    p_desc = (proj.description if proj and proj.description else "") or "Aplicación generada con KOSMO."
                    site_file.write_text(
                        format_site_config(
                            name=p_name,
                            description=p_desc,
                            archetype=ux_analysis.ux_context.archetype.value,
                            primary_color=ux_analysis.ux_context.tokens.primary_color,
                        ),
                        encoding="utf-8",
                    )

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

            plan_prompt = (
                f"{ux_analysis.prompt_block}\n\n"
                f"{project_context}\n\n"
                f"Eres el agente de planificación para la feature '{feature.title}'.\n\n"
                f"## Descripción\n{feature.description}\n\n"
                f"## Requisitos EARS\n{req_markdown}\n\n"
                f"## Diagrama de Actividad\n{diagram.diagram_syntax}\n\n"
                "Propón un plan de implementación detallando los archivos a crear y modificar.\n"
                "OBLIGATORIO: la feature debe entregar una UI funcional con Bootstrap 5. El plan debe incluir:\n"
                "1. El slice autocontenido en `src/features/<slug>/` (manifest.ts, logic.ts, components/).\n"
                "2. La ruta de la feature en `src/app/<slug>/page.tsx`.\n"
                "3. El registro del manifest en `src/lib/feature-registry.ts` "
                "(la navegación del shell se deriva del registro).\n"
                "4. Los tests de la lógica.\n"
                "Lee las skills `kosmo-ui` y `kosmo-nextjs` antes de planificar la UI."
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

            # 8. Fase Build: enviar prompt al Build Agent
            plan_lines = "\n".join(
                f"- [{op.action}] {op.path}" + (f" — {op.description}" if op.description else "")
                for op in impl_plan.operations
            )
            build_prompt = (
                f"{ux_analysis.prompt_block}\n\n"
                f"{project_context}\n\n"
                f"Eres el agente de construcción para la feature '{feature.title}'.\n\n"
                f"## Descripción\n{feature.description}\n\n"
                f"## Requisitos EARS\n{req_markdown}\n\n"
                f"## Diagrama de Actividad\n{diagram.diagram_syntax}\n\n"
                f"## Plan aprobado\n{plan_lines}\n\n"
                "Implementa el código y las pruebas respetando el plan aprobado.\n"
                "OBLIGATORIO: entrega la UI funcional completa de la feature usando 100% Bootstrap 5:\n"
                "1. Lógica de negocio pura en `src/features/<slug>/logic.ts` (con tests en Vitest).\n"
                "2. Componentes en `src/features/<slug>/components/` usando SOLO el design system de "
                "`src/components/ui/` (Button, Card, Input, Label, Badge, Textarea, EmptyState, "
                "PageHeader, Table, Stat, Select, Tabs, Modal, Alert, Steps, BadgeStatus) y clases de Bootstrap 5. "
                "PROHIBIDO el uso de Tailwind CSS.\n"
                "3. Ruta en `src/app/<slug>/page.tsx` que renderiza el componente principal de la feature.\n"
                "4. Registro del manifest en `src/lib/feature-registry.ts` (importa el manifest del slice).\n"
                "5. Actualiza `src/lib/site.ts` con el nombre, descripción y arquetipo reales del proyecto.\n"
                "La UI debe adaptarse a la naturaleza del negocio (ver visión y directivas UX), "
                "mantener el modelo mental del usuario (navegación del registro, estados vacío/error/loading) "
                "y usar textos en español neutro con los mensajes de validación reales de la lógica. "
                "No dejes la feature sin pantalla."
            )

            await _emit(
                OpenCodeEvent(
                    event_type=OpenCodeEventType.BUILD_PROGRESS,
                    session_id=session_id,
                    data={
                        "delta": f"Iniciando generación de código y componentes para '{feature.title}'...",
                        "stage": "building",
                    },
                )
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

            # 9. Fase Validación & Reintentos (hasta max_retries)
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
                    feature_slug=feature.slug,
                    extra_files=generated_files | set(workspace.manifest_files if workspace else ()),
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

            # 10. Conclusión del pipeline
            if validation_result is not None and validation_result.all_passed:
                await _emit(
                    OpenCodeEvent(
                        event_type=OpenCodeEventType.BUILD_PROGRESS,
                        session_id=session_id,
                        data={"delta": "Guardando cambios y publicando vista previa...", "stage": "finishing"},
                    )
                )
                await self._workspace_manager.commit_workspace(
                    feature.project_id,
                    f"feat({feature.slug}): implement feature {feature.display_id} - {feature.title}",
                )
                await self._workspace_manager.publish_preview(feature.project_id)
                impl = dataclasses.replace(
                    impl,
                    status=FeatureImplementationStatus.IMPLEMENTED,
                    generated_files=tuple(sorted(generated_files)),
                    updated_at=datetime.now(UTC),
                )
                await self._implementation_repo.save(impl)

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
                            event_type=OpenCodeEventType.ERROR,
                            session_id=session_id,
                            data={"error": "traceability", "detail": str(exc)},
                        )
                    )

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

                done_event = OpenCodeEvent(
                    event_type=OpenCodeEventType.DONE,
                    session_id=session_id,
                    data={
                        "status": "implemented",
                        "generated_files": list(generated_files),
                        "screens_count": screens_count,
                        "requirements_count": requirements_count,
                        "validations_passed": validations_passed,
                        "validations_total": validations_total,
                        "traceability_edges": traceability_edges,
                        "technologies": ["Next.js", "TypeScript", "Bootstrap 5", "Vitest"],
                    },
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
            if session_id is not None:
                with contextlib.suppress(Exception):
                    await self._opencode_client.close_session(session_id)
            await self._workspace_manager.release_lock(feature.project_id)
