from __future__ import annotations

import re

from kosmo.contracts.sdd.guardrails import (
    PROHIBITED_TERMS,
    GuardrailResult,
    GuardrailViolation,
)

# Mapa de reemplazos para auto-reparación: término técnico → alternativa de negocio
_REPAIR_MAP: dict[str, str] = {
    "base de datos": "almacén de información",
    "database": "almacén de información",
    "SQL": "consultas de información",
    "NoSQL": "almacén de información",
    "API": "servicio de integración",
    "REST": "interfaz de comunicación",
    "GraphQL": "interfaz de consulta",
    "microservicio": "componente del sistema",
    "microservices": "componentes del sistema",
    "servidor": "infraestructura del sistema",
    "server": "infraestructura del sistema",
    "frontend": "interfaz de usuario",
    "backend": "lógica del sistema",
    "framework": "plataforma tecnológica",
    "librería": "componente de software",
    "library": "componente de software",
    "cloud": "plataforma en línea",
    "nube": "plataforma en línea",
    "docker": "entorno de ejecución",
    "kubernetes": "plataforma de orquestación",
    "contenedor": "entorno de ejecución",
    "container": "entorno de ejecución",
    "repositorio": "almacén de código",
    "repository": "almacén de código",
    "endpoint": "punto de acceso",
    "payload": "datos de solicitud",
    "token": "credencial de acceso",
    "JWT": "credencial de acceso",
    "OAuth": "protocolo de autorización",
    "autenticación": "verificación de identidad",
    "authentication": "verificación de identidad",
    "middleware": "componente intermediario",
    "deploy": "publicación del sistema",
    "despliegue": "publicación del sistema",
    "pipeline": "flujo de trabajo",
    "CI/CD": "automatización de entregas",
    "DevOps": "operaciones de desarrollo",
    "compilar": "procesar el código",
    "compile": "procesar el código",
    "runtime": "tiempo de ejecución",
    "caché": "memoria temporal",
    "cache": "memoria temporal",
    "log": "registro de eventos",
    "logging": "registro de eventos",
    "Python": "lenguaje de programación",
    "JavaScript": "lenguaje de programación",
    "TypeScript": "lenguaje de programación",
    "React": "tecnología de interfaz",
    "Next.js": "tecnología de interfaz",
    "FastAPI": "plataforma del sistema",
    "PostgreSQL": "almacén de información",
    "MongoDB": "almacén de información",
    "Redis": "almacén temporal",
}


def detect_technical_terms(text: str) -> GuardrailResult:
    """Detecta términos técnicos prohibidos en el texto generado por la IA.

    Escanea el texto buscando coincidencias con los PROHIBITED_TERMS definidos
    en el contrato de guardrails. La detección es insensible a mayúsculas.

    Args:
        text: El texto generado por la IA a analizar.

    Returns:
        GuardrailResult con passed=True si no hay violaciones,
        o passed=False con la lista de GuardrailViolation encontradas.
    """
    violations: list[GuardrailViolation] = []

    for term in PROHIBITED_TERMS:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        if pattern.search(text):
            violations.append(
                GuardrailViolation(
                    message=(
                        f"Término técnico prohibido detectado: '{term}'. "
                        "El texto de visión de producto no debe contener tecnicismos."
                    )
                )
            )

    if violations:
        return GuardrailResult(passed=False, violations=violations)

    return GuardrailResult(passed=True)


def auto_repair_technical_terms(text: str) -> str:
    """Reemplaza automáticamente los términos técnicos prohibidos por alternativas de negocio.

    Utiliza el mapa interno _REPAIR_MAP para sustituir cada término técnico
    por una expresión equivalente en lenguaje de negocio. El reemplazo preserva
    la capitalización del inicio de oración cuando corresponda.

    Args:
        text: El texto generado por la IA que puede contener términos técnicos.

    Returns:
        El texto con los términos técnicos reemplazados por alternativas de negocio.
        Si un término no tiene reemplazo definido en _REPAIR_MAP, se elimina del texto.
    """
    repaired = text

    # Ordenar por longitud descendente para evitar reemplazos parciales
    # (ej. "base de datos" antes que "datos")
    sorted_terms = sorted(PROHIBITED_TERMS, key=len, reverse=True)

    for term in sorted_terms:
        replacement = _REPAIR_MAP.get(term, "")
        pattern = re.compile(re.escape(term), re.IGNORECASE)

        def _replace_match(match: re.Match[str], repl: str = replacement) -> str:  # noqa: ANN001
            original = match.group(0)
            # Preservar capitalización si el término original empieza en mayúscula
            if original[0].isupper() and repl:
                return repl[0].upper() + repl[1:]
            return repl

        repaired = pattern.sub(_replace_match, repaired)

    return repaired
