from __future__ import annotations

from typing import Any, cast

from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_contexts import EARSPhaseContext
from kosmo.contracts.pipeline.phase_outputs import (
    EARSPhaseOutput,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import FeatureId, RequirementId
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
    def __init__(self) -> None:
        self._feature_id: FeatureId = FeatureId("")
        self._feature_number: int = 0

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
                parameters={
                    "type": "object",
                    "properties": {
                        "requirements": {
                            "type": "array",
                            "description": "Lista de requisitos EARS a validar",
                            "items": {"type": "object"},
                        }
                    },
                    "required": ["requirements"],
                },
            ),
            ToolDefinition(
                name="validate_ears_quality",
                description="Rúbrica 6D de calidad de requisitos",
                parameters={
                    "type": "object",
                    "properties": {
                        "requirements": {
                            "type": "array",
                            "description": "Lista de requisitos EARS a evaluar",
                            "items": {"type": "object"},
                        }
                    },
                    "required": ["requirements"],
                },
            ),
            ToolDefinition(
                name="detect_implementation_leaks",
                description="Escanea términos técnicos prohibidos en requisitos",
                parameters={
                    "type": "object",
                    "properties": {
                        "requirements": {
                            "type": "array",
                            "description": "Lista de requisitos a escanear",
                            "items": {"type": "object"},
                        }
                    },
                    "required": ["requirements"],
                },
            ),
            ToolDefinition(
                name="auto_repair_leaks",
                description="Reemplaza fugas técnicas con lenguaje de negocio",
                parameters={
                    "type": "object",
                    "properties": {
                        "requirements": {
                            "type": "array",
                            "description": "Lista de requisitos a reparar",
                            "items": {"type": "object"},
                        }
                    },
                    "required": ["requirements"],
                },
            ),
        ]

    def build_user_prompt(self, context: EARSPhaseContext) -> str:
        self._feature_id = context.feature.id
        self._feature_number = context.feature_number
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

    def build_output(
        self,
        raw_output: Any,
        validation_result: ValidationResult,
        metadata: GenerationMetadata,
    ) -> EARSPhaseOutput:
        from kosmo.contracts.sdd.document import AcceptanceCriterion
        from kosmo.contracts.sdd.ears import EARSPattern, EARSRequirement
        from kosmo.domain.sdd.id_generator import IdGenerator

        reqs_data = self._extract_requirements_list(raw_output)
        requirements: list[EARSRequirement] = []

        for i, item in enumerate(reqs_data, start=1):
            pattern_str = item.get("pattern", "ubiquitous")  # type: ignore[reportUnknownMemberType]
            try:
                pattern = EARSPattern(str(pattern_str).lower())  # type: ignore[reportUnknownArgumentType]
            except ValueError:
                pattern = EARSPattern.ubiquitous

            raw_ac = item.get("acceptance_criteria", [])
            criteria: list[AcceptanceCriterion] = []
            if isinstance(raw_ac, list):
                for ac in cast(list[object], raw_ac):
                    if isinstance(ac, dict):
                        ac_dict = cast(dict[str, object], ac)
                        criteria.append(
                            AcceptanceCriterion(
                                given=str(ac_dict.get("given", "")),
                                when=str(ac_dict.get("when", "")),
                                then=str(ac_dict.get("then", "")),
                            )
                        )

            raw_trace = item.get("traceability", [])
            traceability: list[str] = (
                [str(t) for t in raw_trace] if isinstance(raw_trace, list)  # type: ignore[reportUnknownVariableType]
                else []
            )

            requirements.append(
                EARSRequirement(
                    id=RequirementId(IdGenerator.generate("requirement")),
                    feature_id=self._feature_id,
                    feature_number=self._feature_number,
                    requirement_number=i,
                    pattern=pattern,
                    trigger=str(item.get("trigger", "")),  # type: ignore[reportUnknownArgumentType]
                    system=str(item.get("system", "")),  # type: ignore[reportUnknownArgumentType]
                    response=str(item.get("response", "")),  # type: ignore[reportUnknownArgumentType]
                    source_statement=str(item.get("source_statement", "")),  # type: ignore[reportUnknownArgumentType]
                    rationale=str(item.get("rationale", "")),  # type: ignore[reportUnknownArgumentType]
                    traceability=traceability,
                    acceptance_criteria=criteria,
                )
            )

        markdown_str = self._requirements_to_markdown(requirements)

        return EARSPhaseOutput(
            feature_id=self._feature_id,
            feature_number=self._feature_number,
            requirements=requirements,
            requirements_markdown=markdown_str,
            validation_result=validation_result,
            generation_metadata=metadata,
        )

    @staticmethod
    def _extract_requirements_list(content: Any) -> list[dict[str, Any]]:
        if isinstance(content, dict):
            raw: object = content.get("requirements", [])  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
            if isinstance(raw, list):
                result: list[dict[str, Any]] = []
                for item in cast(list[object], raw):
                    if isinstance(item, dict):
                        req_dict: dict[str, Any] = {}
                        for k, v in cast(dict[object, object], item).items():
                            if isinstance(k, str):
                                req_dict[k] = v
                        result.append(req_dict)
                return result
        if isinstance(content, list):
            result: list[dict[str, Any]] = []
            for item in cast(list[object], content):
                if isinstance(item, dict):
                    req_dict: dict[str, Any] = {}
                    for k, v in cast(dict[object, object], item).items():
                        if isinstance(k, str):
                            req_dict[k] = v
                    result.append(req_dict)
            return result
        return []

    @staticmethod
    def _requirements_to_markdown(reqs: list[Any]) -> str:
        blocks: list[str] = []
        for r in reqs:
            if hasattr(r, "display_id") and hasattr(r, "source_statement"):
                blocks.append(
                    f"### {r.display_id}\n\n{r.source_statement.strip()}"
                )
        return "\n\n".join(blocks).strip()
