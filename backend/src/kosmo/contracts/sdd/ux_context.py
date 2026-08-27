from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class BusinessArchetype(StrEnum):
    STOREFRONT = "storefront"
    DASHBOARD = "dashboard"
    WORKFLOW = "workflow"
    SAAS_TOOL = "saas_tool"
    CONTENT = "content"


class ShellPattern(StrEnum):
    SIDEBAR = "sidebar"
    TOP_NAV = "top_nav"
    MINIMAL = "minimal"


class DataDensity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class BootstrapDesignTokens:
    primary_color: str = "#0f766e"
    primary_rgb: str = "15, 118, 110"
    font_family_sans: str = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif'
    border_radius: str = "0.5rem"
    border_radius_sm: str = "0.25rem"
    border_radius_lg: str = "0.75rem"
    card_shadow: str = "0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.03)"
    table_density_class: str = "table-sm"
    body_bg: str = "#f8fafc"


@dataclass(frozen=True)
class UXContext:
    archetype: BusinessArchetype
    shell_pattern: ShellPattern
    data_density: DataDensity
    target_users: tuple[str, ...] = field(default_factory=tuple)
    primary_goals: tuple[str, ...] = field(default_factory=tuple)
    recommended_components: tuple[str, ...] = field(default_factory=tuple)
    prohibited_patterns: tuple[str, ...] = field(default_factory=tuple)
    layout_guideline: str = ""
    rationale: str = ""
    tokens: BootstrapDesignTokens = field(default_factory=BootstrapDesignTokens)


@dataclass(frozen=True)
class UXAnalysisOutput:
    ux_context: UXContext
    prompt_block: str
