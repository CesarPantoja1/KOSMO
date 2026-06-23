from __future__ import annotations

import re

from kosmo.contracts.sdd.guardrails import (
    PROHIBITED_TERMS,
    GuardrailResult,
    GuardrailViolation,
)

_TECH_REPLACEMENTS: dict[str, str] = {
    "base de datos": "registro y mantenimiento",
    "almacenará en base de datos": "registrará y mantendrá",
    "enviará una petición HTTP": "comunicará a",
    "validará con el servidor": "verificará",
    "consultará la base de datos": "consultará los registros",
    "guardará en la base de datos": "registrará y mantendrá",
    "almacenar en base de datos": "registrar y mantener",
    "en la base de datos": "en los registros del sistema",
    "via API": "mediante la interfaz del sistema",
    "a través de API": "mediante la interfaz del sistema",
}


def detect_technical_terms(text: str, section: str = "") -> GuardrailResult:
    violations: list[GuardrailViolation] = []
    for term in PROHIBITED_TERMS:
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            idx = match.start()
            start = max(0, idx - 30)
            end = min(len(text), idx + len(term) + 30)
            context = text[start:end]
            violations.append(GuardrailViolation(term=term, context=context, section=section))
    return GuardrailResult(is_valid=len(violations) == 0, violations=violations)


def auto_repair_technical_terms(text: str) -> str:
    result = text
    for original, replacement in _TECH_REPLACEMENTS.items():
        result = result.replace(original, replacement)
    return result


def detect_implementation_leaks(requirements: list[dict[str, str]]) -> GuardrailResult:
    all_violations: list[GuardrailViolation] = []
    for req in requirements:
        text = req.get("source_statement", "") + " " + req.get("response", "")
        result = detect_technical_terms(text, section=req.get("id", ""))
        all_violations.extend(result.violations)
    return GuardrailResult(is_valid=len(all_violations) == 0, violations=all_violations)
