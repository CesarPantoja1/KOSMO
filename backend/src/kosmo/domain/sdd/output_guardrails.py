from __future__ import annotations

import re

from kosmo.contracts.sdd.guardrails import (
    FEATURE_LEVEL_PROHIBITED_TERMS,
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


def detect_feature_level_violations(text: str, section: str = "") -> GuardrailResult:
    violations: list[GuardrailViolation] = []
    all_terms = PROHIBITED_TERMS + FEATURE_LEVEL_PROHIBITED_TERMS
    for term in all_terms:
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            idx = match.start()
            start = max(0, idx - 30)
            end = min(len(text), idx + len(term) + 30)
            context = text[start:end]
            violations.append(GuardrailViolation(term=term, context=context, section=section))
    return GuardrailResult(is_valid=len(violations) == 0, violations=violations)


def detect_implementation_leaks(requirements: list[dict[str, str]]) -> GuardrailResult:
    all_violations: list[GuardrailViolation] = []
    for req in requirements:
        text = req.get("source_statement", "") + " " + req.get("response", "")
        result = detect_technical_terms(text, section=req.get("id", ""))
        all_violations.extend(result.violations)
    return GuardrailResult(is_valid=len(all_violations) == 0, violations=all_violations)


_INJECTION_PATTERNS: list[str] = [
    r"ignora\s+(todas\s+)?las\s+instrucciones",
    r"ignore\s+all\s+instructions",
    r"ya\s+no\s+eres",
    r"you\s+are\s+no\s+longer",
    r"eres\s+(ahora\s+)?un\s+(nuevo\s+)?",
    r"you\s+are\s+now\s+a\s+",
    r"desde\s+ahora\s+eres",
    r"from\s+now\s+on\s+you\s+are",
    r"cambia\s+tu\s+rol\s+a",
    r"change\s+your\s+role\s+to",
    r"tu\s+nuevo\s+rol\s+es",
    r"your\s+new\s+role\s+is",
    r"en\s+adelante\s+ser[aá]s",
    r"a\s+partir\s+de\s+ahora",
    r"ahora\s+vas\s+a\s+ser",
    r"olvida\s+todo\s+lo\s+anterior",
    r"forget\s+everything",
    r"act[uú]a\s+como\s+(si\s+fueras\s+)?un\s+",
    r"reinicia\s+tus\s+instrucciones",
    r"tu\s+nuevo\s+sistema\s+de\s+prompt",
    r"eres\s+libre\s+de",
    r"you\s+are\s+free\s+to",
    r"no\s+sigas\s+las\s+instrucciones",
    r"do\s+not\s+follow\s+the\s+instructions",
    r"sistema:\s*$",
    r"^system:\s*",
    r"\[system\]",
    r"<\|im_start\|>",
    r"<\|system\|>",
    r"\[INST\]",
    r"\[\\INST\]",
]

_INSTRUCTION_MAX_LENGTH = 2000


def sanitize_user_instructions(text: str) -> str:
    if not text or not text.strip():
        return text

    if len(text) > _INSTRUCTION_MAX_LENGTH:
        raise ValueError(f"Las instrucciones no pueden exceder {_INSTRUCTION_MAX_LENGTH} caracteres.")

    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise ValueError(
                "Las instrucciones contienen patrones no permitidos. "
                "Por favor reformula tu solicitud sin intentar modificar "
                "el comportamiento base del asistente."
            )

    return text.strip()
