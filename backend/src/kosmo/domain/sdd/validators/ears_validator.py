from __future__ import annotations

import re
from typing import Any, cast

from kosmo.contracts.pipeline.phase_outputs import ValidationResult
from kosmo.contracts.sdd.document import EARSPattern, EARSPattern_SYNTAX

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
    r"^(si\s+.+\s+(no\s+funciona|falla|fallare|error|fallo))\s*,?\s*"
    r"(el sistema|la aplicación)\s+(shall|debe|deberá)\s+",
    re.IGNORECASE,
)
_COMPLEX_RE = re.compile(
    r"^(mientras|durante|en\s+estado\s+de)\s+.+\s+(y|además|cuando|al)\s+", re.IGNORECASE
)


def _get(req: Any, key: str, default: Any = "") -> Any:
    if isinstance(req, dict):
        d = cast("dict[str, Any]", req)
        return d.get(key, default)
    return getattr(req, key, default)


def _get_source_statement(req: Any) -> str:
    return str(_get(req, "source_statement", ""))


def _get_pattern(req: Any) -> EARSPattern | str:
    val = _get(req, "pattern", "")
    if isinstance(val, EARSPattern):
        return val
    try:
        return EARSPattern(str(val))
    except ValueError:
        return str(val)


def _get_display_id(req: Any) -> str:
    if isinstance(req, dict):
        d = cast("dict[str, Any]", req)
        fn = d.get("feature_number", 0)
        rn = d.get("requirement_number", 0)
        return f"REQ-{fn}.{rn}"
    return str(_get(req, "display_id", "REQ-?.?"))


def _get_acceptance_criteria(req: Any) -> list[Any]:
    ac = _get(req, "acceptance_criteria", [])
    if isinstance(ac, list):
        return cast("list[Any]", ac)
    return []


def validate_ears_syntax(requirements: list[Any]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    for req in requirements:
        stmt = _get_source_statement(req)
        pattern = _get_pattern(req)
        display_id = _get_display_id(req)

        if pattern == EARSPattern.ubiquitous and not _UBIQUITOUS_RE.match(stmt):
            errors.append(
                f"{display_id}: Sintaxis ubiquitous incorrecta. "
                f"Esperado: '{EARSPattern_SYNTAX[EARSPattern.ubiquitous]}'. "
                f"Obtenido: '{stmt[:80]}'"
            )

        elif pattern == EARSPattern.event_driven and not _EVENT_DRIVEN_RE.match(stmt):
            warnings.append(
                f"{display_id}: Posible sintaxis event-driven incorrecta. "
                f"Esperado inicio con 'CUANDO/al'. Obtenido: '{stmt[:80]}'"
            )

        elif pattern == EARSPattern.state_driven and not _STATE_DRIVEN_RE.match(stmt):
            warnings.append(
                f"{display_id}: Posible sintaxis state-driven incorrecta. "
                f"Esperado inicio con 'MIENTRAS/durante'. Obtenido: '{stmt[:80]}'"
            )

        elif pattern == EARSPattern.optional and not _OPTIONAL_RE.match(stmt):
            warnings.append(
                f"{display_id}: Posible sintaxis optional incorrecta. "
                f"Esperado inicio con 'DONDE/si'. Obtenido: '{stmt[:80]}'"
            )

        elif pattern == EARSPattern.unwanted and not _UNWANTED_RE.match(stmt):
            warnings.append(
                f"{display_id}: Posible sintaxis unwanted incorrecta. "
                f"Esperado inicio con 'SI ... falla'. Obtenido: '{stmt[:80]}'"
            )

        elif pattern == EARSPattern.complex and not _COMPLEX_RE.match(stmt):
            warnings.append(
                f"{display_id}: Posible sintaxis complex incorrecta. "
                f"Esperado inicio con 'MIENTRAS ... Y ...'. Obtenido: '{stmt[:80]}'"
            )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_ears_quality(requirements: list[Any]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if len(requirements) < 3:
        errors.append(
            f"Se requieren al menos 3 requisitos por feature, solo hay {len(requirements)}"
        )
    elif len(requirements) > 15:
        warnings.append(f"Se recomienda máximo 15 requisitos por feature, hay {len(requirements)}")

    patterns_seen: set[str] = set()
    for req in requirements:
        pattern = _get_pattern(req)
        patterns_seen.add(str(pattern))
        display_id = _get_display_id(req)
        stmt = _get_source_statement(req)
        ac = _get_acceptance_criteria(req)

        if not stmt.strip():
            errors.append(f"{display_id}: source_statement vacío")

        if not ac:
            warnings.append(f"{display_id}: sin criterios de aceptación")

    if len(patterns_seen) < 4:
        warnings.append(
            f"Se recomiendan al menos 4 categorías EARS diferentes, solo hay {len(patterns_seen)}"
        )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
