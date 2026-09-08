from __future__ import annotations

import contextlib
from pathlib import Path

from kosmo.contracts.sdd.codegen import (
    FeatureImplementationRepository,
    FeatureImplementationStatus,
    FileAction,
    FileOperation,
    FileSystemReader,
    ValidationRunResult,
)
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import (
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
)
from kosmo.contracts.sdd.ux_context import UXAnalysisOutput
from kosmo.domain.codegen.parse_validation_output import (
    derive_fix_directives,
    format_validation_errors_for_prompt,
)
from kosmo.domain.codegen.path_safety import UnsafePathError, sanitize_relative_path
from kosmo.domain.codegen.site_config import format_site_config
from kosmo.domain.sdd.document_converters import document_to_markdown


class NullFileSystemReader(FileSystemReader):
    """Implementación nula de FileSystemReader por defecto cuando no se suministra lector."""

    def list_files(self, root: str | Path) -> tuple[str, ...]:
        del root
        return ()

    def read_text(self, path: str | Path) -> str | None:
        del path
        return None


def normalize_generated_file_path(raw_path: str, workspace_dir: str) -> str | None:
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


def collect_workspace_feature_files(
    workspace_dir: str | Path,
    feature_slug: str,
    fs_reader: FileSystemReader | None = None,
) -> set[str]:
    """Recolecta archivos generados o modificados para la feature usando el puerto FileSystemReader."""
    reader = fs_reader or NullFileSystemReader()
    files: set[str] = set()
    all_files = reader.list_files(workspace_dir)
    normalized_slug = feature_slug.strip().lower()
    slice_pattern = f"src/features/{normalized_slug}/"
    app_pattern = f"src/app/{normalized_slug}/"
    for raw_f in all_files:
        norm_f = raw_f.replace("\\", "/").strip("./")
        norm_lower = norm_f.lower()
        if (
            norm_lower.startswith(slice_pattern)
            or norm_lower.startswith(app_pattern)
            or norm_lower in ("src/lib/feature-registry.ts", "src/lib/site.ts", "src/db/schema.ts")
        ):
            files.add(norm_f)
    return files


def get_existing_db_schema_context(
    workspace_dir: str | None,
    fs_reader: FileSystemReader | None = None,
) -> str:
    """Lee el esquema Drizzle existente de src/db/schema.ts usando el puerto FileSystemReader."""
    if not workspace_dir or fs_reader is None:
        return ""
    ws_str = str(workspace_dir).replace("\\", "/").rstrip("/")
    schema_path = f"{ws_str}/src/db/schema.ts"
    content = fs_reader.read_text(schema_path)
    if content is None:
        content = fs_reader.read_text("src/db/schema.ts")
    if content and content.strip():
        return f"\n### Esquema de base de datos actual (`src/db/schema.ts`)\n```typescript\n{content.strip()}\n```"
    return ""


class ImplementationContextBuilder:
    """Construye contextos enriquecidos y prompts para el pipeline de implementación de features."""

    def __init__(
        self,
        project_repo: ProjectRepository | None = None,
        document_repo: DocumentRepository | None = None,
        implementation_repo: FeatureImplementationRepository | None = None,
        feature_repo: FeatureRepository | None = None,
        fs_reader: FileSystemReader | None = None,
    ) -> None:
        self._project_repo = project_repo
        self._document_repo = document_repo
        self._implementation_repo = implementation_repo
        self._feature_repo = feature_repo
        self._fs_reader = fs_reader or NullFileSystemReader()

    def normalize_file_path(self, raw_path: str, workspace_dir: str) -> str | None:
        """Normaliza una ruta usando la función de seguridad."""
        return normalize_generated_file_path(raw_path, workspace_dir)

    def collect_feature_files(self, workspace_dir: str | Path, feature_slug: str) -> set[str]:
        """Recolecta archivos de la feature en el workspace usando el lector configurado."""
        return collect_workspace_feature_files(workspace_dir, feature_slug, self._fs_reader)

    def get_db_schema_context(self, workspace_dir: str | None) -> str:
        """Obtiene el contexto del esquema de base de datos si existe."""
        return get_existing_db_schema_context(workspace_dir, self._fs_reader)

    async def build_project_context(
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
        implemented_context = await self.build_implemented_features_context(
            project_id=project_id,
            current_feature_id=current_feature_id,
        )
        if implemented_context:
            lines.append(f"\n### Funcionalidades ya implementadas en el proyecto\n{implemented_context}")

        # Contexto de base de datos existente
        if workspace_dir:
            db_context = self.get_db_schema_context(workspace_dir)
            if db_context:
                lines.append(db_context)

        return "\n".join(lines)

    async def build_implemented_features_context(
        self,
        project_id: ProjectId,
        current_feature_id: FeatureId | None = None,
    ) -> str:
        """Construye un resumen conciso de funcionalidades ya implementadas para evitar duplicación."""
        if self._implementation_repo is None:
            return ""

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
        if self._feature_repo is not None:
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

    async def sync_site_config(
        self,
        workspace_dir: str,
        project_id: ProjectId,
        ux_analysis: UXAnalysisOutput,
    ) -> None:
        """Sincroniza site.ts con el arquetipo y tokens reales del análisis UX."""
        site_file = Path(workspace_dir) / "src" / "lib" / "site.ts"
        if not site_file.exists() or self._project_repo is None:
            return

        with contextlib.suppress(Exception):
            proj = await self._project_repo.by_id(project_id)
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

    def build_plan_prompt(
        self,
        feature: Feature,
        req_markdown: str,
        diagram_syntax: str,
        ux_prompt_block: str,
        project_context: str,
    ) -> str:
        """Construye el prompt para el Plan Agent de OpenCode."""
        return (
            f"{ux_prompt_block}\n\n"
            f"{project_context}\n\n"
            f"Eres el agente de planificación para la feature '{feature.title}'.\n\n"
            f"## Descripción\n{feature.description}\n\n"
            f"## Requisitos EARS\n{req_markdown}\n\n"
            f"## Diagrama de Actividad\n{diagram_syntax}\n\n"
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

    def build_fallback_plan_operations(
        self,
        feature: Feature,
        feature_slug: str,
        manifest_files: tuple[str, ...],
    ) -> list[FileOperation]:
        """Genera el conjunto canónico de operaciones de contingencia si el Plan Agent no produjo operaciones."""
        existing_manifest = set(manifest_files)
        registry_action = FileAction.MODIFY if "src/lib/feature-registry.ts" in existing_manifest else FileAction.CREATE
        return [
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

    def build_build_prompt(
        self,
        feature: Feature,
        req_markdown: str,
        diagram_syntax: str,
        ux_prompt_block: str,
        project_context: str,
        plan_lines: str,
    ) -> str:
        """Construye el prompt para el Build Agent de OpenCode."""
        return (
            f"{ux_prompt_block}\n\n"
            f"{project_context}\n\n"
            f"Eres el agente de construcción para la feature '{feature.title}'.\n\n"
            f"## Descripción\n{feature.description}\n\n"
            f"## Requisitos EARS\n{req_markdown}\n\n"
            f"## Diagrama de Actividad\n{diagram_syntax}\n\n"
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

    def build_fix_prompt(
        self,
        attempt: int,
        max_retries: int,
        validation_result: ValidationRunResult,
    ) -> str:
        """Construye el prompt de corrección para el Build Agent a partir de los errores de validación."""
        error_feedback = format_validation_errors_for_prompt(
            validation_result,
            max_chars=6000,
        )
        directives = derive_fix_directives(validation_result)
        directives_block = "\n".join(f"- {d}" for d in directives)

        return (
            f"La validación falló en el intento {attempt}/{max_retries}.\n\n"
            f"## Errores detectados:\n{error_feedback}\n\n"
            f"## Directivas de corrección:\n{directives_block}"
        )
