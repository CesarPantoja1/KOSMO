from __future__ import annotations

import re

from kosmo.contracts.pipeline.phase_outputs import ValidationResult
from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.contracts.sdd.guardrails import DISCOVERY_SECTIONS
from kosmo.domain.sdd.output_guardrails import detect_technical_terms

_HU_PATTERN_RE = re.compile(r"Como\s+.+\s+quiero\s+.+\s+para\s+", re.IGNORECASE)
_NUMBERED_ITEM_RE = re.compile(r"^\s*\d+\.\s+\S", re.MULTILINE)
_BULLET_ITEM_RE = re.compile(r"^\s*[-*]\s+\S", re.MULTILINE)
_EXCLUDED_BLOCK_RE = re.compile(
    r"^#{0,6}\s*Excluido\s*$\n(.*?)(?=^\s*#{1,6}\s|\Z)",
    re.IGNORECASE | re.DOTALL | re.MULTILINE,
)

_GOALS_SECTION = "Metas del producto"
_RULES_SECTION = "Reglas de negocio"
_SCOPE_SECTION = "Alcance"

MIN_GOALS = 2
MIN_RULES = 4
MIN_EXCLUSIONS = 3


def _group_sections(doc: RichTextDocument) -> list[tuple[str, str]]:
    """Agrupa cada encabezado con el contenido que le sigue hasta el próximo encabezado."""
    groups: list[tuple[str, str]] = []
    current_heading: str | None = None
    current_content: list[str] = []

    def flush() -> None:
        if current_heading is not None:
            groups.append((current_heading, "\n".join(current_content).strip()))

    for node in doc.nodes:
        if node.type == "heading" and node.heading:
            flush()
            current_heading = node.heading.text
            current_content = [node.content] if node.content else []
        elif node.content:
            current_content.append(node.content)

    flush()
    return groups


def _find_content(groups: list[tuple[str, str]], section: str) -> str | None:
    for heading, content in groups:
        if section.lower() in heading.lower():
            return content
    return None


def validate_discovery_structure(
    doc: RichTextDocument,
    min_words_per_section: int = 25,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    groups = _group_sections(doc)
    found_sections: dict[str, int] = {}
    for section in DISCOVERY_SECTIONS:
        content = _find_content(groups, section)
        if content is not None:
            found_sections[section] = len(content.split())

    for section in DISCOVERY_SECTIONS:
        if section not in found_sections:
            errors.append(f"Seccion faltante: {section}")
        elif found_sections[section] < min_words_per_section:
            errors.append(
                f"Seccion '{section}' tiene solo {found_sections[section]} palabras (minimo {min_words_per_section})"
            )

    goals_content = _find_content(groups, _GOALS_SECTION)
    if goals_content is not None:
        goal_count = len(_NUMBERED_ITEM_RE.findall(goals_content))
        if goal_count < MIN_GOALS:
            errors.append(f"Seccion '{_GOALS_SECTION}' tiene {goal_count} metas (minimo {MIN_GOALS})")

    rules_content = _find_content(groups, _RULES_SECTION)
    if rules_content is not None:
        rule_count = len(_NUMBERED_ITEM_RE.findall(rules_content))
        if rule_count < MIN_RULES:
            errors.append(f"Seccion '{_RULES_SECTION}' tiene {rule_count} reglas (minimo {MIN_RULES})")

    if _find_content(groups, _SCOPE_SECTION) is not None:
        from kosmo.domain.sdd.document_converters import document_to_markdown

        excluded_match = _EXCLUDED_BLOCK_RE.search(document_to_markdown(doc))
        exclusion_count = len(_BULLET_ITEM_RE.findall(excluded_match.group(1))) if excluded_match else 0
        if exclusion_count < MIN_EXCLUSIONS:
            errors.append(f"Alcance tiene {exclusion_count} exclusiones explicitas (minimo {MIN_EXCLUSIONS})")

    missing = len(DISCOVERY_SECTIONS) - len(found_sections)
    if missing > 0:
        warnings.append(f"Se encontraron {len(found_sections)} de {len(DISCOVERY_SECTIONS)} secciones requeridas")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_discovery_quality(doc: RichTextDocument) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    full_text_parts: list[str] = []

    for node in doc.nodes:
        if not node.content:
            continue
        section_name = node.heading.text if node.heading else ""
        result = detect_technical_terms(node.content, section=section_name)
        if not result.is_valid:
            for violation in result.violations:
                errors.append(
                    f"Termino tecnico prohibido '{violation.term}' encontrado "
                    f"en seccion '{violation.section}': {violation.context}"
                )
        full_text_parts.append(node.content)

    full_text = "\n".join(full_text_parts)
    if _HU_PATTERN_RE.search(full_text):
        errors.append(
            "Se detecto formato de Historia de Usuario "
            "('Como... quiero... para...'). El Descubrimiento opera a nivel de "
            "negocio; usa declaraciones verificables, no escenarios de interaccion."
        )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
