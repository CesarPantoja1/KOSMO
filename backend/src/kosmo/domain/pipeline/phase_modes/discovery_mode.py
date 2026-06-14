from __future__ import annotations

from typing import Any

from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_contexts import DiscoveryPhaseContext
from kosmo.contracts.pipeline.phase_outputs import ValidationResult
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.pipeline.phase_validators.discovery_validator import (
    validate_discovery_quality,
    validate_discovery_structure,
)

_DISCOVERY_SYSTEM_PROMPT = (
    "Eres un analista de negocio sénior. Aplicás ReAct internamente.\n"
    "Generá el documento directamente, sin texto introductorio.\n"
    "La primera línea del documento debe ser '## Visión del producto'.\n"
    "No uses formato de historia de usuario (Como... quiero... para...).\n"
    "No menciones tecnología ni implementación.\n"
    "Todo en español con tildes correctas.\n\n"
    "## Visión del producto\n\n"
    "[Párrafo de 2-4 oraciones. Describe qué hace el producto, para quién,\n"
    "y cuál es su propósito central.]\n\n"
    "## Espacio del problema\n\n"
    "[Describe el problema de negocio que resuelve. Quiénes lo sufren.\n"
    "Consecuencias de no resolverlo.]\n\n"
    "## Actores\n\n"
    "[Lista de actores. Formato: '- **Actor:** descripción de su rol e interés.']\n\n"
    "## Propuesta de valor\n\n"
    "[Para cada actor, su beneficio concreto. Formato:\n"
    "'- **Para Actor:** beneficio concreto.']\n\n"
    "## Casos de uso\n\n"
    "[Casos de uso resumidos, una línea por caso. Formato numerado:\n"
    "'1. **Nombre del caso:** descripción breve de la interacción.'\n"
    "Mínimo 4. Cada actor debe aparecer en al menos uno.]\n\n"
    "## Capacidades principales\n\n"
    "[Lista de funcionalidades clave. Formato:\n"
    "'- **Capacidad:** descripción breve de lo que permite.']\n\n"
    "## Reglas de negocio\n\n"
    "[Reglas verificables. Formato: '1. Condición específica y verificable.'\n"
    "Mínimo 4.]\n\n"
    "## Atributos de calidad\n\n"
    "[Requisitos no funcionales en lenguaje de negocio. Formato:\n"
    "'- **Atributo:** descripción medible desde perspectiva del usuario.']\n\n"
    "## Alcance\n\n"
    "*Incluido:*\n"
    "- Ítem incluido\n\n"
    "*Excluido:*\n"
    "- Ítem excluido (mínimo 3)\n\n"
    "*Futuro potencial:*\n"
    "- Mejora futura\n\n"
    "REGLAS DE GENERACIÓN (no incluir en el documento):\n"
    "- PROHIBIDO: API, base de datos, microservicios, endpoints, servidores, "
    "lenguajes, frameworks, protocolos, arquitectura, deployment, Docker, "
    "cloud, SQL, HTTP, REST, GraphQL, backend, frontend, cache, Redis, "
    "MongoDB, PostgreSQL, Kubernetes, AWS, GCP, Azure.\n"
    "- NO generes texto antes de '## Visión del producto'.\n"
    "- Cada sección con contenido sustancial.\n"
    "- Casos de uso resumidos, una línea por caso.\n"
    "- Reglas de negocio verificables, no ambiguas.\n"
    "- Al menos 3 exclusiones explícitas en Alcance.\n"
    "- NUNCA uses formato 'Como... quiero... para...'.\n"
    "- NO incluyas esta sección de instrucciones en tu respuesta.\n"
    "- Tu respuesta debe contener ÚNICAMENTE las 9 secciones del documento,\n"
    "  comenzando con '## Visión del producto' y terminando con '## Alcance'.\n"
)


class DiscoveryMode:
    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.DESCUBRIMIENTO

    @property
    def system_prompt(self) -> str:
        return _DISCOVERY_SYSTEM_PROMPT

    @property
    def available_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="validate_discovery_structure",
                description="Verifica que el documento tiene 9 secciones con contenido mínimo",
            ),
            ToolDefinition(
                name="validate_discovery_quality",
                description="Detecta jerga técnica, secciones vacías, términos prohibidos",
            ),
        ]

    def build_user_prompt(self, context: DiscoveryPhaseContext) -> str:
        parts = [
            "## Proyecto\n",
            f"**Nombre:** {context.project_name}",
            f"**Descripción:** {context.project_description}",
        ]
        if context.user_preferences:
            prefs = "\n".join(f"- {p.rule_text}" for p in context.user_preferences)
            parts.append(f"\n## Preferencias del usuario\n\n{prefs}")
        return "\n".join(parts)

    def validate_output(self, output: Any) -> ValidationResult:
        from kosmo.domain.sdd.document_converters import markdown_to_document

        raw_text = ""
        if isinstance(output, dict) and "document" in output:
            raw_text = output["document"]
        elif isinstance(output, dict) and "raw_text" in output:
            raw_text = output["raw_text"]
        elif isinstance(output, str):
            raw_text = output
        else:
            return ValidationResult(
                is_valid=False,
                errors=["Formato de salida no reconocido"],
            )

        raw_text = self._pre_repair(raw_text)
        doc = markdown_to_document(raw_text)

        structure_result = validate_discovery_structure(doc)
        quality_result = validate_discovery_quality(doc)

        all_errors = structure_result.errors + quality_result.errors
        all_warnings = structure_result.warnings + quality_result.warnings

        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
        )

    @staticmethod
    def _pre_repair(text: str) -> str:
        from kosmo.domain.sdd.output_guardrails import auto_repair_technical_terms

        return auto_repair_technical_terms(text)

    def build_retry_prompt(
        self,
        original_prompt: str,
        errors: list[str],
        retry_count: int,
    ) -> str:
        error_list = "\n".join(f"- {e}" for e in errors)
        return (
            f"{original_prompt}\n\n"
            f"## Correcciones necesarias (intento {retry_count})\n\n"
            f"El documento generado tiene los siguientes problemas:\n\n"
            f"{error_list}\n\n"
            f"Corrige estos problemas y genera el documento completo nuevamente.\n"
            f"Recordá: no escribas texto introductorio, comenzá directamente con "
            f"'## Visión del producto'. Los casos de uso deben ser resumidos, "
            f"una línea por caso."
        )
