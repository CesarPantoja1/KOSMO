from __future__ import annotations

from typing import Any

from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_contexts import DiscoveryPhaseContext
from kosmo.contracts.pipeline.phase_outputs import (
    DiscoveryPhaseOutput,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.pipeline.phase_validators.discovery_validator import (
    validate_discovery_quality,
    validate_discovery_structure,
)

_DISCOVERY_SYSTEM_PROMPT = (
    "Eres un analista de negocio sénior. Aplicas ReAct internamente.\n"
    "El Descubrimiento opera EXCLUSIVAMENTE a nivel de negocio: captura y valida "
    "el entendimiento del dominio del problema y la oportunidad que el producto "
    "aborda, sin referencia alguna a tecnología, componentes de software ni a "
    "cómo el usuario interactúa con la interfaz.\n"
    "Genera el documento directamente, sin texto introductorio.\n"
    "La primera línea del documento debe ser '## Visión del producto'.\n"
    "No uses formato de historia de usuario (Como... quiero... para...).\n"
    "No menciones tecnología ni implementación.\n"
    "Todo en español con tildes correctas.\n\n"
    "## Visión del producto\n\n"
    "[Declaración fundacional de 2-4 oraciones que alinea a todos los involucrados. "
    "Presenta la razón de existir del producto, el público al que se dirige y su "
    "propósito central.]\n\n"
    "## Espacio del problema\n\n"
    "[Describe la situación actual que motiva el producto: quiénes padecen el "
    "problema, en qué contexto se manifiesta y las consecuencias de no resolverlo. "
    "Establece la brecha entre la realidad del usuario y la solución deseada.]\n\n"
    "## Actores\n\n"
    "[Personas, roles u organizaciones que interactúan con el producto o se ven "
    "afectados por él. Formato: '- **Actor:** rol, interés principal y relación "
    "con el problema.']\n\n"
    "## Propuesta de valor\n\n"
    "[Beneficio concreto y diferenciador para cada actor identificado. Formato:\n"
    "'- **Para el Actor:** mejora tangible que obtiene al usar el producto.']\n\n"
    "## Metas del producto\n\n"
    "[Metas de alto nivel que el negocio necesita lograr para resolver el problema. "
    "Cada meta empieza con un título de máximo 5 palabras que nombra el área de "
    "negocio, seguido de una declaración verificable. Formato:\n"
    "'1. **Título del área:** declaración verificable de lo que el negocio necesita "
    "lograr.'\n"
    "Mínimo 2. Las metas NO describen escenarios de interacción ni nombran actores "
    "específicos.]\n\n"
    "## Reglas de negocio\n\n"
    "[Restricciones, condiciones y políticas del dominio. Cada regla es una "
    "afirmación verificable que define una condición que siempre debe cumplirse. "
    "Formato: '1. Condición específica y verificable.'\n"
    "Mínimo 4.]\n\n"
    "## Alcance\n\n"
    "### Incluido\n"
    "- Ítem incluido\n\n"
    "### Excluido\n"
    "- Ítem excluido (mínimo 3)\n\n"
    "### Futuro potencial\n"
    "- Mejora futura\n\n"
    "REGLAS DE GENERACIÓN (no incluir en el documento):\n"
    "- PROHIBIDO: API, base de datos, microservicios, endpoints, servidores, "
    "lenguajes, frameworks, protocolos, arquitectura, deployment, Docker, "
    "cloud, SQL, HTTP, REST, GraphQL, backend, frontend, cache, Redis, "
    "MongoDB, PostgreSQL, Kubernetes, AWS, GCP, Azure.\n"
    "- NO generes texto antes de '## Visión del producto'.\n"
    "- Cada sección con contenido sustancial.\n"
    "- Las metas son declaraciones de negocio verificables, sin actores ni "
    "escenarios de interacción.\n"
    "- Reglas de negocio verificables, no ambiguas (mínimo 4).\n"
    "- Al menos 3 exclusiones explícitas en Alcance.\n"
    "- NUNCA uses formato 'Como... quiero... para...'.\n"
    "- NO incluyas esta sección de instrucciones en tu respuesta.\n"
    "- Tu respuesta debe contener ÚNICAMENTE las 7 secciones del documento,\n"
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
                description=("Verifica que el documento tiene 7 secciones con contenido mínimo"),
                parameters={
                    "type": "object",
                    "properties": {
                        "document": {
                            "type": "string",
                            "description": ("El documento de descubrimiento completo en formato markdown"),
                        }
                    },
                    "required": ["document"],
                },
            ),
            ToolDefinition(
                name="validate_discovery_quality",
                description="Detecta jerga técnica, secciones vacías, términos prohibidos",
                parameters={
                    "type": "object",
                    "properties": {
                        "document": {
                            "type": "string",
                            "description": ("El documento de descubrimiento a evaluar en formato markdown"),
                        }
                    },
                    "required": ["document"],
                },
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
        from kosmo.domain.sdd.output_guardrails import auto_repair_technical_terms

        raw_text: str = ""
        if isinstance(output, dict) and "document" in output:
            raw_text = str(output["document"])  # type: ignore[reportUnknownArgumentType]
        elif isinstance(output, dict) and "raw_text" in output:
            raw_text = str(output["raw_text"])  # type: ignore[reportUnknownArgumentType]
        elif isinstance(output, str):
            raw_text = output
        else:
            return ValidationResult(
                is_valid=False,
                errors=["Formato de salida no reconocido"],
            )

        raw_text = auto_repair_technical_terms(raw_text)
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
            f"Recuerda: no escribas texto introductorio, comienza directamente con "
            f"'## Visión del producto'. Mantén todo a nivel de negocio; las metas "
            f"del producto son declaraciones verificables, sin actores ni escenarios "
            f"de interacción."
        )

    def build_output(
        self,
        raw_output: Any,
        validation_result: ValidationResult,
        metadata: GenerationMetadata,
    ) -> DiscoveryPhaseOutput:
        from kosmo.domain.sdd.document_converters import (
            coerce_markdown_output,
            markdown_to_document,
        )

        doc = markdown_to_document(coerce_markdown_output(raw_output))
        return DiscoveryPhaseOutput(
            discovery_document=doc,
            validation_result=validation_result,
            generation_metadata=metadata,
        )
