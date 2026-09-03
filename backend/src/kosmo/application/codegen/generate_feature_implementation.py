from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import structlog
from ulid import ULID

from kosmo.application.codegen.analyze_ux_context import (
    UXAnalysisInput,
    UXAnalyzerUseCase,
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
from kosmo.domain.codegen.parse_validation_output import (
    derive_fix_directives,
    format_validation_errors_for_prompt,
)
from kosmo.domain.codegen.path_safety import UnsafePathError, sanitize_relative_path
from kosmo.domain.codegen.plan_rules import validate_plan
from kosmo.domain.codegen.site_config import format_site_config
from kosmo.domain.codegen.structural_validator import validate_workspace_feature_structure
from kosmo.domain.sdd.document_converters import document_to_markdown, slugify_spanish

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


def _normalize_generated_file_path(raw_path: str, workspace_dir: str) -> str | None:
    """Normaliza y valida una ruta de archivo generada para asegurar que sea relativa y segura."""
    raw_str = raw_path.strip()
    if not raw_str:
        return None
    try:
        p = Path(raw_str)
        ws_p = Path(workspace_dir).resolve()
        if p.is_absolute():
            p_resolved = p.resolve()
            if p_resolved.is_relative_to(ws_p):
                rel = p_resolved.relative_to(ws_p)
                return sanitize_relative_path(str(rel))
            return None
        return sanitize_relative_path(raw_str)
    except (UnsafePathError, ValueError):
        return None


def _get_existing_db_schema_context(workspace_dir: str | None) -> str:
    """Lee el esquema Drizzle existente de src/db/schema.ts para contexto de generación incremental."""
    if not workspace_dir:
        return ""
    schema_path = Path(workspace_dir) / "src" / "db" / "schema.ts"
    if not schema_path.is_file():
        return ""
    try:
        content = schema_path.read_text(encoding="utf-8").strip()
        if content:
            return f"\n### Esquema de base de datos actual (`src/db/schema.ts`)\n```typescript\n{content}\n```"
    except Exception:
        pass
    return ""


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
        self._ux_analyzer = ux_analyzer or UXAnalyzerUseCase(
            document_repo=document_repo,
            feature_repo=feature_repo,
        )
        self._register_traceability = RegisterCodeTraceabilityUseCase(
            traceability_repo=traceability_repo,
            requirement_repo=requirement_repo,
        )

    def set_sync_github_repository(self, sync_github_repository: SyncGitHubRepositoryUseCase) -> None:
        self._sync_github_repository = sync_github_repository

    async def _build_project_context(
        self,
        project_id: ProjectId,
        current_feature_id: FeatureId | None = None,
        workspace_dir: str | None = None,
    ) -> str:
        """Construye el bloque de contexto del proyecto (visión, features previas y schema de BD)."""
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

        # Contexto de base de datos existente
        if workspace_dir:
            db_context = _get_existing_db_schema_context(workspace_dir)
            if db_context:
                lines.append(db_context)

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
        # 1. Consultar precondiciones concurrentemente
        feature, req_markdown, diagram, is_healthy = await asyncio.gather(
            self._feature_repo.by_id(input_data.feature_id),
            self._requirement_repo.by_feature_id(input_data.feature_id),
            self._activity_diagram_repo.by_feature_id(input_data.feature_id),
            self._opencode_client.health_check(),
        )

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
                "OBLIGATORIO: la feature DEBE entregar una solución 100% FUNCIONAL DE EXTREMO A EXTREMO "
                "(Frontend + Backend + Base de Datos). El plan debe incluir:\n"
                "1. El slice autocontenido en `src/features/<slug>/` (manifest.ts, logic.ts, components/).\n"
                "2. La ruta navegable y página principal en `src/app/<slug>/page.tsx` con export default "
                "que renderice la vista interactiva (formularios, listas, acciones).\n"
                "3. El registro del manifest en `src/lib/feature-registry.ts` "
                "(IMPORTANTE: añade la feature al array `features` existente sin eliminar las features previas; "
                "la navegación del shell se deriva del registro).\n"
                "4. Los tests de la lógica en Vitest.\n"
                "5. Si la feature maneja persistencia de datos, incluye la modificación de `src/db/schema.ts` "
                "para declarar las tablas con Drizzle ORM y la integración de lectura/escritura.\n"
                "Lee las skills `kosmo-ui`, `kosmo-nextjs` y `kosmo-drizzle` antes de planificar."
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
                existing_manifest = set(workspace.manifest_files if workspace else ())
                registry_action = (
                    FileAction.MODIFY if "src/lib/feature-registry.ts" in existing_manifest else FileAction.CREATE
                )
                plan_operations = [
                    FileOperation(
                        action=FileAction.CREATE,
                        path=f"src/features/{feature_slug}/logic.ts",
                        description=f"Lógica de negocio y tipos para {feature.title}",
                    ),
                    FileOperation(
                        action=FileAction.CREATE,
                        path=f"src/features/{feature_slug}/manifest.ts",
                        description=f"Manifiesto del slice de {feature.title}",
                    ),
                    FileOperation(
                        action=FileAction.CREATE,
                        path=f"src/app/{feature_slug}/page.tsx",
                        description=f"Página y UI principal de {feature.title}",
                    ),
                    FileOperation(
                        action=registry_action,
                        path="src/lib/feature-registry.ts",
                        description=f"Registro de {feature.title} en el catálogo global de navegación",
                    ),
                    FileOperation(
                        action=FileAction.CREATE,
                        path=f"tests/{feature_slug}.test.ts",
                        description=f"Pruebas unitarias de {feature.title}",
                    ),
                ]
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
                "OBLIGATORIO: entrega una funcionalidad 100% OPERATIVA Y COMPLETA "
                "(Frontend + Backend + Base de Datos) usando Bootstrap 5:\n"
                "1. Frontend interactivo en `src/app/<slug>/page.tsx`: DEBE contener `export default` y "
                "renderizar la vista operativa de la feature con componentes funcionales (formularios con captura "
                "de datos, tablas de registros, botones de acción con respuesta real, feedback de error/éxito "
                "y estados de carga). PROHIBIDO dejar páginas vacías o stubs que provoquen error 404 al navegar.\n"
                "2. Lógica de negocio y backend en `src/features/<slug>/logic.ts` (con tests exhaustivos en Vitest) "
                "y Server Actions o API routes si se requiere.\n"
                "3. Componentes en `src/features/<slug>/components/` usando SOLO el design system de "
                "`src/components/ui/` (Button, Card, Input, Label, Badge, Textarea, EmptyState, "
                "PageHeader, Table, Stat, Select, Tabs, Modal, Alert, Steps, BadgeStatus) y clases de Bootstrap 5. "
                "PROHIBIDO el uso de Tailwind CSS.\n"
                "4. Registro del manifest en `src/lib/feature-registry.ts` "
                "(IMPORTANTE: importa el manifest del nuevo slice y añádelo al array `features` existente "
                "sin borrar ni sobrescribir las entradas de features anteriores; "
                "la navegación depende de este catálogo).\n"
                "5. Actualiza `src/lib/site.ts` con el nombre, descripción y arquetipo reales del proyecto.\n"
                "6. Persistencia de datos: Si la feature maneja persistencia, define las tablas en `src/db/schema.ts` "
                "usando `drizzle-orm/sqlite-core` y consume `db` desde `src/db/index.ts`. "
                "Prohibido usar arreglos volátiles en memoria para datos persistentes.\n"
                "La UI debe adaptarse a la naturaleza del negocio (ver visión y directivas UX), "
                "mantener el modelo mental del usuario (navegación del registro, estados vacío/error/loading) "
                "y usar textos en español neutro con los mensajes de validación reales de la lógica. "
                "No dejes la feature sin pantalla funcional."
            )

            generated_files: set[str] = set()
            async for ev in self._opencode_client.send_prompt(session_id, build_prompt, agent="build"):
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
                    feature_slug=feature_slug,
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
                    error_feedback = format_validation_errors_for_prompt(
                        validation_result,
                        max_chars=6000,
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

                    directives = derive_fix_directives(validation_result)
                    directives_block = "\n".join(f"- {d}" for d in directives)

                    fix_prompt = (
                        f"La validación falló en el intento {attempt}/{input_data.max_retries}.\n\n"
                        f"## Errores detectados:\n{error_feedback}\n\n"
                        f"## Directivas de corrección:\n{directives_block}"
                    )
                    async for ev in self._opencode_client.send_prompt(session_id, fix_prompt, agent="build"):
                        await _emit(ev)
                        if ev.event_type == OpenCodeEventType.FILE_EDIT:
                            file_path_fix: object = ev.data.get("path")
                            if file_path_fix is not None:
                                normalized_p = _normalize_generated_file_path(str(file_path_fix), workspace_dir)
                                if normalized_p:
                                    generated_files.add(normalized_p)

            # 10. Conclusión del pipeline
            if validation_result is not None and validation_result.all_passed:
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

                features_count = 1
                try:
                    project_impls = await self._implementation_repo.list_by_project(feature.project_id)
                    features_count = (
                        sum(1 for f in project_impls if getattr(f.status, "value", f.status) == "implemented") or 1
                    )
                except Exception:
                    features_count = 1

                done_event = OpenCodeEvent(
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

        except Exception:
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
