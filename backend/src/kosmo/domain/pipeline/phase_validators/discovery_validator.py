from __future__ import annotations

import re

from kosmo.contracts.pipeline.phase_outputs import ValidationResult
from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.contracts.sdd.guardrails import DISCOVERY_SECTIONS
from kosmo.domain.sdd.output_guardrails import detect_technical_terms

_HU_PATTERN_RE = re.compile(r"Como\s+.+\s+quiero\s+.+\s+para\s+", re.IGNORECASE)
_CU_SECTION = "Casos de uso"


def validate_discovery_structure(
    doc: RichTextDocument,
    min_words_per_section: int = 25,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    found_sections: dict[str, int] = {}

    for node in doc.nodes:
        if node.type == "heading" and node.heading:
            heading_text = node.heading.text.lower()
            for section in DISCOVERY_SECTIONS:
                if section.lower() in heading_text:
                    word_count = len(node.content.split()) if node.content else 0
                    found_sections[section] = word_count

    for section in DISCOVERY_SECTIONS:
        if section not in found_sections:
            errors.append(f"Seccion faltante: {section}")
        elif found_sections[section] < min_words_per_section:
            errors.append(
                f"Seccion '{section}' tiene solo {found_sections[section]} palabras "
                f"(minimo {min_words_per_section})"
            )

    missing = len(DISCOVERY_SECTIONS) - len(found_sections)
    if missing > 0:
        warnings.append(
            f"Se encontraron {len(found_sections)} de {len(DISCOVERY_SECTIONS)} "
            f"secciones requeridas"
        )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_discovery_quality(doc: RichTextDocument) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    cu_content = ""

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

        if _CU_SECTION.lower() in section_name.lower():
            cu_content = node.content

    if cu_content and _HU_PATTERN_RE.search(cu_content):
        errors.append(
            "Casos de uso: se detecto formato de Historia de Usuario "
            "('Como... quiero... para...'). Usa formato resumido: "
            "'1. **Nombre:** descripcion breve.'"
        )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
