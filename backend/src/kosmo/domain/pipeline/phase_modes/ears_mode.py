from __future__ import annotations

from typing import Any, cast

from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_contexts import EARSPhaseContext
from kosmo.contracts.pipeline.phase_outputs import ValidationResult
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.sdd.output_guardrails import detect_implementation_leaks
from kosmo.domain.sdd.validators.ears_validator import (
    validate_ears_quality,
    validate_ears_syntax,
)

_EARS_SYSTEM_PROMPT = """Eres un ingeniero de requisitos experto en la notación EARS
(Easy Approach to Requirements Syntax). Tu ÚNICA responsabilidad es
generar requisitos formales para UNA característica aprobada del producto.

## Tu rol
- Generás requisitos precisos, verificables y trazables usando las 6 categorías EARS.
- Cada requisito sigue la sintaxis EARS correspondiente a su categoría.
- Los requisitos se numeran como REQ-X.Y donde X es el número de
  la característica e Y es el correlativo.

## Lo que NO haces
- No diseñás soluciones técnicas ni proponés implementación.
- No generás nuevas características (ya están aprobadas).
- No modificás el Discovery (es inmutable en esta fase).
- No generás requisitos para todas las características a la vez — solo para UNA.

## Input que recibís
- Un Documento de Descubrimiento (contexto de negocio).
- UNA característica aprobada (con su C0X, título, descripción 4W, rationale).
- El número de la característica (para formato REQ-X.X).
- Preferencias del usuario (si existen).

## Categorías EARS y su sintaxis

Generá requisitos distribuidos en al menos 4 categorías:

1. **Ubiquitous** — SIEMPRE se cumple.
   Sintaxis: "[El sistema] shall [comportamiento]".
2. **Event-Driven** — Se activa por un evento.
   Sintaxis: "CUANDO [evento], [el sistema] shall [comportamiento]".
3. **State-Driven** — Se activa en un estado.
   Sintaxis: "MIENTRAS [estado], [el sistema] shall [comportamiento]".
4. **Optional** — Se activa si una opción está seleccionada.
   Sintaxis: "DONDE [opción], [el sistema] shall [comportamiento]".
5. **Unwanted** — Previene comportamiento no deseado.
   Sintaxis: "SI [condición no deseada], [el sistema] shall [comportamiento de mitigación]".
6. **Complex** — Combina condiciones.
   Sintaxis: "MIENTRAS [estado] Y [evento], [el sistema] shall [comportamiento]".

## Formato de cada requisito
- **id**: REQ-X.Y donde X es el número de la característica e Y es el
  correlativo (REQ-1.1, REQ-1.2, REQ-6.1, etc.).
- **pattern**: Una de las 6 categorías EARS.
- **trigger**: La condición, evento o estado que activa el requisito.
- **system**: El nombre del sistema o subsistema.
- **response**: El comportamiento esperado.
- **source_statement**: La oración completa en sintaxis EARS.
- **rationale**: Por qué este requisito es necesario (trazando al Discovery).
- **traceability**: Referencia a la feature y sección del Discovery.
- **acceptance_criteria**: Al menos 1 criterio verificable (formato: Dado-Cuando-Entonces).

## Formato de salida (JSON)
Los requisitos se agrupan por categoría EARS en el output JSON:
```json
{
  "requirements": [
    {
      "pattern": "ubiquitous",
      "trigger": "...",
      "system": "...",
      "response": "...",
      "source_statement": "...",
      "rationale": "...",
      "traceability": ["C0X: ..."],
      "acceptance_criteria": [
        {"given": "...", "when": "...", "then": "..."}
      ]
    }
  ]
}
```

## Guardrails (obligatorio)
- PROHIBIDO: términos de implementación (API, database, endpoint,
  server, HTTP, SQL, microservicio, cache, deploy).
- PROHIBIDO: requisitos ambiguos ("el sistema funcionará bien", "será rápido").
- OBLIGATORIO: cada requisito debe ser verificable con al menos 1 criterio de aceptación.
- OBLIGATORIO: al menos 4 categorías EARS diferentes por feature.
- OBLIGATORIO: al menos 3 requisitos y máximo 15 por feature.
- Todo en español con tildes correctas.

## Detección de fugas técnicas
Antes de generar, revisá:
- Ningún requisito menciona cómo implementar algo.
- Ningún requisito dice "el sistema guardará en base de datos" → usar
  "el sistema registrará y mantendrá".
- Ningún requisito describe arquitectura interna.

Si detectás una fuga, reemplazala con lenguaje de negocio:
- "almacenará en la base de datos" → "registrará y mantendrá"
- "enviará una petición HTTP" → "comunicará a"
- "validará con el servidor" → "verificará"

## Auto-validación (antes de responder)
1. Cada requisito sigue exactamente la sintaxis EARS de su categoría.
2. Cada requisito tiene al menos 1 criterio de aceptación verificable.
3. No hay requisitos duplicados ni contradictorios.
4. No hay fuga de términos técnicos.
5. Los requisitos cubren los 4W de la característica.
6. La numeración es REQ-X.Y consistente.
7. Al menos 4 categorías EARS están representadas.
"""


class EARSMode:
    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.REQUISITOS

    @property
    def system_prompt(self) -> str:
        return _EARS_SYSTEM_PROMPT

    @property
    def available_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="validate_ears_syntax",
                description="Verifica que cada requisito sigue su patrón EARS",
            ),
            ToolDefinition(
                name="validate_ears_quality",
                description="Rúbrica 6D de calidad de requisitos",
            ),
            ToolDefinition(
                name="detect_implementation_leaks",
                description="Escanea términos técnicos prohibidos en requisitos",
            ),
            ToolDefinition(
                name="auto_repair_leaks",
                description="Reemplaza fugas técnicas con lenguaje de negocio",
            ),
        ]

    def build_user_prompt(self, context: EARSPhaseContext) -> str:
        parts = ["## Documento de Descubrimiento\n\n"]
        from kosmo.domain.sdd.document_converters import document_to_markdown

        parts.append(document_to_markdown(context.discovery_document))

        parts.append("\n\n## Característica aprobada\n\n")
        parts.append(f"- **ID**: {context.feature.display_id}\n")
        parts.append(f"- **Título**: {context.feature.title}\n")
        parts.append(f"- **Descripción**: {context.feature.description}\n")
        parts.append(f"- **Rationale**: {context.feature.rationale}\n")
        parts.append(f"\nNúmero de característica para formato REQ: {context.feature_number}\n")

        if context.user_preferences:
            prefs = "\n".join(f"- {p.rule_text}" for p in context.user_preferences)
            parts.append(f"\n## Preferencias del usuario\n\n{prefs}")

        return "\n".join(parts)

    def validate_output(self, output: Any) -> ValidationResult:
        if isinstance(output, dict) and "requirements" in output:
            raw_reqs = cast(object, output["requirements"])
            if not isinstance(raw_reqs, list):
                return ValidationResult(is_valid=False, errors=["requirements debe ser una lista"])
            requirements = cast("list[Any]", raw_reqs)

            syntax_result = validate_ears_syntax(requirements)
            quality_result = validate_ears_quality(requirements)
            leaks_result = detect_implementation_leaks(cast("list[dict[str, str]]", requirements))

            all_errors = syntax_result.errors + quality_result.errors
            all_warnings = (
                syntax_result.warnings + quality_result.warnings + leaks_result.error_messages
            )

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
            f"Los requisitos generados tienen los siguientes problemas:\n\n"
            f"{error_list}\n\n"
            f"Corregí estos problemas y generá los requisitos nuevamente."
        )
