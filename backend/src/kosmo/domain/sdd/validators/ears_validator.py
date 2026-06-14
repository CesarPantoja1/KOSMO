from __future__ import annotations

import re

from kosmo.contracts.pipeline.phase_outputs import ValidationResult
from kosmo.contracts.sdd.document import EARSPattern, EARSPattern_SYNTAX
from kosmo.contracts.sdd.ears import EARSRequirement

_UBIQUITOUS_RE = re.compile(
    r"^(el sistema|la aplicación|el sistema)\s+(shall|debe|deberá)\s+", re.IGNORECASE
)
_EVENT_DRIVEN_RE = re.compile(
    r"^(cuando|al|al\s+producirse|al\s+ocurrir|al\s+recibir)\s+", re.IGNORECASE
)
_STATE_DRIVEN_RE = re.compile(
    r"^(mientras|durante|en\s+estado\s+de|bajo\s+la\s+condición\s+de)\s+", re.IGNORECASE
)
_OPTIONAL_RE = re.compile(r"^(donde|si|en\s+caso\s+de\s+que|opcionalmente)\s+", re.IGNORECASE)
_UNWANTED_RE = re.compile(
    r"^(si\s+.+\s+(no\s+funciona|falla|fallare|error|fallo))\s*,?\s*(el sistema|la aplicación)\s+(shall|debe|deberá)\s+",
    re.IGNORECASE,
)
_COMPLEX_RE = re.compile(
    r"^(mientras|durante|en\s+estado\s+de)\s+.+\s+(y|además|cuando|al)\s+", re.IGNORECASE
)


def validate_ears_syntax(requirements: list[EARSRequirement]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    for req in requirements:
        stmt = req.source_statement
        pattern = req.pattern

        if pattern == EARSPattern.ubiquitous:
            if not _UBIQUITOUS_RE.match(stmt):
                errors.append(
                    f"{req.display_id}: Sintaxis ubiquitous incorrecta. "
                    f"Esperado: '{EARSPattern_SYNTAX[EARSPattern.ubiquitous]}'. "
                    f"Obtenido: '{stmt[:80]}'"
                )

        elif pattern == EARSPattern.event_driven:
            if not _EVENT_DRIVEN_RE.match(stmt):
                warnings.append(
                    f"{req.display_id}: Posible sintaxis event-driven incorrecta. "
                    f"Esperado inicio con 'CUANDO/al'. Obtenido: '{stmt[:80]}'"
                )

        elif pattern == EARSPattern.state_driven:
            if not _STATE_DRIVEN_RE.match(stmt):
                warnings.append(
                    f"{req.display_id}: Posible sintaxis state-driven incorrecta. "
                    f"Esperado inicio con 'MIENTRAS/durante'. Obtenido: '{stmt[:80]}'"
                )

        elif pattern == EARSPattern.optional:
            if not _OPTIONAL_RE.match(stmt):
                warnings.append(
                    f"{req.display_id}: Posible sintaxis optional incorrecta. "
                    f"Esperado inicio con 'DONDE/si'. Obtenido: '{stmt[:80]}'"
                )

        elif pattern == EARSPattern.unwanted:
            if not _UNWANTED_RE.match(stmt):
                warnings.append(
                    f"{req.display_id}: Posible sintaxis unwanted incorrecta. "
                    f"Esperado inicio con 'SI ... falla'. Obtenido: '{stmt[:80]}'"
                )

        elif pattern == EARSPattern.complex:
            if not _COMPLEX_RE.match(stmt):
                warnings.append(
                    f"{req.display_id}: Posible sintaxis complex incorrecta. "
                    f"Esperado inicio con 'MIENTRAS ... Y ...'. Obtenido: '{stmt[:80]}'"
                )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_ears_quality(requirements: list[EARSRequirement]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if len(requirements) < 3:
        errors.append(
            f"Se requieren al menos 3 requisitos por feature, solo hay {len(requirements)}"
        )
    elif len(requirements) > 15:
        warnings.append(f"Se recomienda máximo 15 requisitos por feature, hay {len(requirements)}")

    patterns_seen: set[EARSPattern] = set()
    for req in requirements:
        patterns_seen.add(req.pattern)

        if not req.source_statement.strip():
            errors.append(f"{req.display_id}: source_statement vacío")

        if not req.acceptance_criteria:
            warnings.append(f"{req.display_id}: sin criterios de aceptación")

    if len(patterns_seen) < 4:
        warnings.append(
            f"Se recomiendan al menos 4 categorías EARS diferentes, solo hay {len(patterns_seen)}"
        )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
