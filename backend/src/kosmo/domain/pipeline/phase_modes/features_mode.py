from __future__ import annotations

from typing import Any

from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_contexts import FeaturesPhaseContext
from kosmo.contracts.pipeline.phase_outputs import ValidationResult
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.pipeline.phase_validators.features_validator import (
    validate_features_semantic,
    validate_features_structure,
)

_FEATURES_SYSTEM_PROMPT = """Eres un diseñador de producto experto. Tu ÚNICA responsabilidad es descomponer un Documento de Descubrimiento en Características (Features) del producto.

## Tu rol
- Transformás las capacidades y casos de uso del Discovery en características concretas del producto.
- Cada característica tiene un identificador en formato C0X (C01, C02, C03, C04, C05) y una descripción en formato 4W.

## Lo que NO haces
- No generás requisitos formales (EARS). Eso es otra fase.
- No inventás características que no se derivan del Discovery.
- No diseñás arquitectura técnica ni implementación.

## Input que recibís
- Un Documento de Descubrimiento con 9 secciones de negocio.
- La lista de preferencias del usuario (si existen).
- La lista de títulos de features ya existentes (para evitar duplicados).

## Formato de salida
Generá EXACTAMENTE 5 características. Cada una con:

- **display_id**: C0X donde X es el número correlativo (C01, C02, C03, C04, C05).
- **title**: Nombre corto y descriptivo (máximo 6 palabras).
- **description**: Descripción en formato 4W:
  - QUÉ hace la característica.
  - PARA QUIÉN está destinada (actor del Discovery).
  - BAJO QUÉ CONDICIÓN se activa o es relevante.
  - QUÉ VALOR entrega al actor o al negocio.
- **rationale**: Por qué esta característica es esencial (2-3 oraciones, trazando al Discovery).
- **inferred_from**: Secciones del Discovery de las que se deriva (referencias específicas).

## Guardrails (obligatorio)
- PROHIBIDO mencionar: API, base de datos, microservicios, endpoints, lenguajes, frameworks, protocolos técnicos.
- NO Parafrasees: cada característica debe representar una capacidad DISTINTA del producto.
- NO Seas Trivial: las características deben ser agregaciones de valor, no traducciones literales de casos de uso.
- Cada característica debe trazar a al menos una sección del Discovery (inferred_from no vacío).
- Los 4W de la descripción deben ser específicos, no genéricos.
- Todo en español con tildes correctas.

## Anti-duplicación
Antes de generar, verificá:
1. Ninguna característica duplica o solapa significativamente otra.
2. Las 5 características juntas cubren todas las capacidades del Discovery.

## Auto-validación (antes de responder)
1. Cada característica tiene los 4W completos y específicos.
2. Cada `inferred_from` referencia secciones reales del Discovery.
3. No hay duplicación semántica entre características.
4. Las 5 características cubren los actores y casos de uso del Discovery.
5. No hay jerga técnica en ninguna descripción.
"""


class FeaturesMode:
    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.CARACTERISTICAS

    @property
    def system_prompt(self) -> str:
        return _FEATURES_SYSTEM_PROMPT

    @property
    def available_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="validate_features_structure",
                description="Verifica título (máx 6 palabras) y descripción 4W por feature",
            ),
            ToolDefinition(
                name="validate_features_semantic",
                description="Anti-trivialidad, anti-paráfrasis, no solapamiento",
            ),
        ]

    def build_user_prompt(self, context: FeaturesPhaseContext) -> str:
        parts = ["## Documento de Descubrimiento\n\n"]
        from kosmo.domain.sdd.document_converters import document_to_markdown

        parts.append(document_to_markdown(context.discovery_document))

        if context.existing_feature_titles:
            titles = ", ".join(context.existing_feature_titles)
            parts.append(f"\n\n## Características ya existentes (NO duplicar)\n\n{titles}")

        if context.user_preferences:
            prefs = "\n".join(f"- {p.rule_text}" for p in context.user_preferences)
            parts.append(f"\n\n## Preferencias del usuario\n\n{prefs}")

        return "\n".join(parts)

    def validate_output(self, output: Any) -> ValidationResult:
        if isinstance(output, dict) and "features" in output:
            features = output["features"]
            if not isinstance(features, list):
                return ValidationResult(is_valid=False, errors=["features debe ser una lista"])

            structure_result = validate_features_structure(features)
            discovery = output.get("discovery_document")
            semantic_result = validate_features_semantic(features, discovery)

            all_errors = structure_result.errors + semantic_result.errors
            all_warnings = structure_result.warnings + semantic_result.warnings

            return ValidationResult(
                is_valid=len(all_errors) == 0,
                errors=all_errors,
                warnings=all_warnings,
            )

        return ValidationResult(is_valid=False, errors=["Formato de salida no reconocido"])

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
            f"Las características generadas tienen los siguientes problemas:\n\n"
            f"{error_list}\n\n"
            f"Corregí estos problemas y generá las características nuevamente."
        )
