from __future__ import annotations

import re
from dataclasses import dataclass

from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository, FeatureRepository
from kosmo.contracts.sdd.ux_context import (
    BootstrapDesignTokens,
    BusinessArchetype,
    DataDensity,
    ShellPattern,
    UXAnalysisOutput,
    UXContext,
)
from kosmo.domain.sdd.document_converters import document_to_markdown

ARCHETYPE_KEYWORDS: dict[BusinessArchetype, frozenset[str]] = {
    BusinessArchetype.STOREFRONT: frozenset(
        {
            "venta",
            "ventas",
            "catalogo",
            "catálogo",
            "inventario",
            "precio",
            "precios",
            "producto",
            "productos",
            "tienda",
            "compra",
            "compras",
            "cliente",
            "clientes",
            "pedido",
            "pedidos",
            "reserva",
            "reservas",
            "carrito",
        }
    ),
    BusinessArchetype.DASHBOARD: frozenset(
        {
            "reporte",
            "reportes",
            "metrica",
            "metricas",
            "métrica",
            "métricas",
            "analitica",
            "analítica",
            "estadistica",
            "estadística",
            "estadisticas",
            "estadísticas",
            "monitoreo",
            "kpi",
            "control",
            "indicador",
            "indicadores",
            "gasto",
            "gastos",
            "saldo",
            "saldos",
            "balance",
            "balances",
            "finanzas",
            "financiero",
        }
    ),
    BusinessArchetype.WORKFLOW: frozenset(
        {
            "flujo",
            "aprobacion",
            "aprobación",
            "proceso",
            "etapa",
            "etapas",
            "estado",
            "estados",
            "gestion",
            "gestión",
            "tramite",
            "trámite",
            "solicitud",
            "solicitudes",
            "auditoria",
            "auditoría",
            "seguimiento",
        }
    ),
    BusinessArchetype.CONTENT: frozenset(
        {
            "contenido",
            "articulo",
            "artículo",
            "articulos",
            "artículos",
            "publicacion",
            "publicación",
            "blog",
            "documento",
            "documentos",
            "noticia",
            "noticias",
            "educativo",
            "curso",
            "cursos",
            "leccion",
            "lección",
        }
    ),
}

THEME_TOKENS_BY_ARCHETYPE: dict[BusinessArchetype, BootstrapDesignTokens] = {
    BusinessArchetype.DASHBOARD: BootstrapDesignTokens(
        primary_color="#4f46e5",
        primary_rgb="79, 70, 229",
        font_family_sans='system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
        border_radius="0.375rem",
        border_radius_sm="0.25rem",
        border_radius_lg="0.5rem",
        card_shadow="0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)",
        table_density_class="table-sm",
        body_bg="#f8fafc",
    ),
    BusinessArchetype.STOREFRONT: BootstrapDesignTokens(
        primary_color="#0f766e",
        primary_rgb="15, 118, 110",
        font_family_sans='system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
        border_radius="0.5rem",
        border_radius_sm="0.25rem",
        border_radius_lg="0.75rem",
        card_shadow="0 4px 6px -1px rgba(0,0,0,0.08), 0 2px 4px -2px rgba(0,0,0,0.04)",
        table_density_class="table",
        body_bg="#ffffff",
    ),
    BusinessArchetype.WORKFLOW: BootstrapDesignTokens(
        primary_color="#2563eb",
        primary_rgb="37, 99, 235",
        font_family_sans='system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
        border_radius="0.375rem",
        border_radius_sm="0.25rem",
        border_radius_lg="0.5rem",
        card_shadow="0 1px 3px rgba(0,0,0,0.05)",
        table_density_class="table-sm",
        body_bg="#f8fafc",
    ),
    BusinessArchetype.CONTENT: BootstrapDesignTokens(
        primary_color="#7c3aed",
        primary_rgb="124, 58, 237",
        font_family_sans='Georgia, Cambria, "Times New Roman", Times, serif',
        border_radius="0.5rem",
        border_radius_sm="0.25rem",
        border_radius_lg="0.75rem",
        card_shadow="0 2px 4px rgba(0,0,0,0.05)",
        table_density_class="table",
        body_bg="#fafafa",
    ),
    BusinessArchetype.SAAS_TOOL: BootstrapDesignTokens(
        primary_color="#0f766e",
        primary_rgb="15, 118, 110",
        font_family_sans='system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
        border_radius="0.5rem",
        border_radius_sm="0.25rem",
        border_radius_lg="0.75rem",
        card_shadow="0 1px 3px rgba(0,0,0,0.05)",
        table_density_class="table",
        body_bg="#f8fafc",
    ),
}


@dataclass(frozen=True)
class UXAnalysisInput:
    feature_id: FeatureId
    project_id: ProjectId


def classify_archetype(discovery_text: str, feature_title: str = "", feature_desc: str = "") -> BusinessArchetype:
    """Clasifica el arquetipo de negocio determinísticamente mediante conteo de keywords."""
    combined = f"{discovery_text} {feature_title} {feature_desc}".lower()
    words = set(re.findall(r"\w+", combined))

    scores: dict[BusinessArchetype, int] = {arch: len(words & kw) for arch, kw in ARCHETYPE_KEYWORDS.items()}

    best_arch = max(scores, key=lambda k: scores[k])
    if scores[best_arch] > 0:
        return best_arch

    return BusinessArchetype.SAAS_TOOL


class UXAnalyzerUseCase:
    """Analizador determinista de UX y arquitectura de información contextual."""

    def __init__(
        self,
        document_repo: DocumentRepository | None = None,
        feature_repo: FeatureRepository | None = None,
    ) -> None:
        self._document_repo = document_repo
        self._feature_repo = feature_repo

    async def execute(self, input_data: UXAnalysisInput) -> UXAnalysisOutput:
        discovery_md = ""
        if self._document_repo is not None:
            discovery_doc = await self._document_repo.get_discovery(input_data.project_id)
            if discovery_doc is not None:
                discovery_md = document_to_markdown(discovery_doc)

        feature: Feature | None = None
        if self._feature_repo is not None:
            feature = await self._feature_repo.by_id(input_data.feature_id)

        feature_title = feature.title if feature else ""
        feature_desc = feature.description if feature else ""

        archetype = self.classify_archetype(discovery_md, feature_title, feature_desc)
        target_users = self._extract_actors(discovery_md)
        primary_goals = self._extract_goals(discovery_md)

        shell_pattern, data_density, components, prohibited, layout_guide, rationale = self._derive_ux_rules(
            archetype, feature_title, feature_desc
        )

        tokens = THEME_TOKENS_BY_ARCHETYPE.get(archetype, THEME_TOKENS_BY_ARCHETYPE[BusinessArchetype.SAAS_TOOL])

        ux_context = UXContext(
            archetype=archetype,
            shell_pattern=shell_pattern,
            data_density=data_density,
            target_users=tuple(target_users),
            primary_goals=tuple(primary_goals),
            recommended_components=tuple(components),
            prohibited_patterns=tuple(prohibited),
            layout_guideline=layout_guide,
            rationale=rationale,
            tokens=tokens,
        )

        prompt_block = self._build_prompt_block(ux_context)

        return UXAnalysisOutput(ux_context=ux_context, prompt_block=prompt_block)

    def classify_archetype(
        self, discovery_text: str, feature_title: str = "", feature_desc: str = ""
    ) -> BusinessArchetype:
        return classify_archetype(discovery_text, feature_title, feature_desc)

    def _classify_archetype(self, discovery_text: str, feature_title: str, feature_desc: str) -> BusinessArchetype:
        return classify_archetype(discovery_text, feature_title, feature_desc)

    def _extract_actors(self, discovery_text: str) -> list[str]:
        actors: list[str] = []
        if "## Actores" in discovery_text:
            section = discovery_text.split("## Actores")[1].split("##")[0]
            for line in section.split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    clean = line.lstrip("-* ").replace("**", "").strip()
                    if clean:
                        actors.append(clean)
        return actors[:5]

    def _extract_goals(self, discovery_text: str) -> list[str]:
        goals: list[str] = []
        if "## Metas del producto" in discovery_text:
            section = discovery_text.split("## Metas del producto")[1].split("##")[0]
            for line in section.split("\n"):
                line = line.strip()
                if re.match(r"^\d+\.", line) or line.startswith("-"):
                    clean = re.sub(r"^\d+\.\s*", "", line).lstrip("-* ").replace("**", "").strip()
                    if clean:
                        goals.append(clean)
        return goals[:5]

    def _derive_ux_rules(
        self, archetype: BusinessArchetype, _feature_title: str, _feature_desc: str
    ) -> tuple[ShellPattern, DataDensity, list[str], list[str], str, str]:
        if archetype == BusinessArchetype.DASHBOARD:
            return (
                ShellPattern.SIDEBAR,
                DataDensity.HIGH,
                ["PageHeader", "Stat", "Table", "Card", "BadgeStatus", "Select", "Button"],
                [
                    "Grid de cards como vista de datos principal",
                    "Hero banner publicitario",
                    "Textos genéricos o lorem ipsum",
                    "Navegación horizontal exclusiva",
                ],
                "Usa PageHeader con acciones principales a la derecha, fila de KPIs (Stat) arriba, "
                "y Table estructurada con filtros (Select / Input) para los registros. Evita Cards repetitivas.",
                "El dominio contiene métricas, balances o reportes operativos con alta densidad de información.",
            )
        if archetype == BusinessArchetype.STOREFRONT:
            return (
                ShellPattern.TOP_NAV,
                DataDensity.LOW,
                ["PageHeader", "Card", "Badge", "Button", "Input", "Modal", "EmptyState"],
                [
                    "Tablas densas de backoffice sin imágenes ni resúmenes",
                    "Sidebar abrumador de administración",
                    "Interfaces grises sin acentos de color atractivos",
                ],
                "Usa PageHeader claro, filtros por categoría arriba y un grid de Cards con imágenes/iconos, "
                "precios/cantidades y botón de acción principal bien visible.",
                "El dominio está orientado a catálogo, reservas o productos con interacción de selección y compra.",
            )
        if archetype == BusinessArchetype.WORKFLOW:
            return (
                ShellPattern.SIDEBAR,
                DataDensity.MEDIUM,
                ["PageHeader", "Steps", "Card", "BadgeStatus", "Input", "Select", "Textarea", "Button", "Alert"],
                [
                    "Formularios largos en una sola columna sin pasos ni agrupamiento",
                    "Ausencia de feedback visual de estado (BadgeStatus)",
                    "Ocultar el progreso de la tarea",
                ],
                "Estructura la pantalla con Steps si es un flujo secuencial, usa Card agrupadas con títulos "
                "claros para cada sección de datos y BadgeStatus para indicar el estado del proceso.",
                "El dominio requiere ejecución de trámites, aprobaciones o etapas con trazabilidad de estado.",
            )
        if archetype == BusinessArchetype.CONTENT:
            return (
                ShellPattern.MINIMAL,
                DataDensity.LOW,
                ["PageHeader", "Card", "Tabs", "Badge", "Button", "EmptyState"],
                [
                    "Tablas compactas de datos numéricos",
                    "Exceso de botones y controles por pantalla",
                ],
                "Prioriza la legibilidad tipográfica en un contenedor centrado (col-lg-8 mx-auto), "
                "organiza el contenido por Tabs o secciones limpias.",
                "El dominio es de documentación, artículos o contenido informativo.",
            )

        return (
            ShellPattern.TOP_NAV,
            DataDensity.MEDIUM,
            ["PageHeader", "Card", "Table", "Input", "Button", "Badge", "Alert", "EmptyState"],
            [
                "Diseños sobrecargados",
                "Textos de bienvenida genéricos",
            ],
            "Estructura funcional directa: PageHeader con título, formulario conciso o listado de registros "
            "con acciones claras y validación visible.",
            "Aplicación SaaS con herramientas y utilidades interactivas.",
        )

    def _build_prompt_block(self, ctx: UXContext) -> str:
        prohibited_list = "\n".join(f"- {p}" for p in ctx.prohibited_patterns)
        components_list = ", ".join(ctx.recommended_components)

        return (
            "## Directivas de UX y Arquitectura de UI (NON-NEGOTIABLE)\n"
            f"- **Arquetipo de negocio:** `{ctx.archetype.value}`\n"
            f"- **Navegación / Shell:** `{ctx.shell_pattern.value}`\n"
            f"- **Densidad de datos requerida:** `{ctx.data_density.value}`\n"
            f"- **Componentes del Design System recomendados:** `{components_list}`\n"
            f"- **Pauta de Layout:** {ctx.layout_guideline}\n"
            f"- **Fundamento de Diseño:** 100% Bootstrap 5 (clases `container`, `row`, `col-*`, `d-flex`, `gap-*`). "
            "PROHIBIDO el uso de Tailwind CSS.\n\n"
            f"### Patrones PROHIBIDOS en esta Feature:\n"
            f"{prohibited_list}\n\n"
            f"**Razonamiento UX:** {ctx.rationale}"
        )
