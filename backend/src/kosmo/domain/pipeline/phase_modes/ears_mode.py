from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel

from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_contexts import EARSPhaseContext
from kosmo.contracts.pipeline.phase_outputs import (
    EARSPhaseOutput,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import AcceptanceCriterion, EARSPattern, SpecPhase
from kosmo.contracts.sdd.ids import FeatureId, RequirementId
from kosmo.domain.sdd.validators.ears_validator import (
    validate_ears_quality,
    validate_ears_software_level,
    validate_ears_syntax,
)

_EARS_SYSTEM_PROMPT = """Eres un ingeniero de requisitos experto en la notación EARS
(Easy Approach to Requirements Syntax). Tu ÚNICA responsabilidad es
generar requisitos a nivel de SOFTWARE para UNA característica aprobada.

## Tu rol
- Generas requisitos precisos, verificables y trazables usando las 6 categorías EARS.
- Cada requisito sigue la sintaxis EARS correspondiente a su categoría.
- Los requisitos se numeran como REQ-X.Y donde X es el número de
  la característica e Y es el correlativo.
- En este nivel de software puedes nombrar componentes del sistema,
  subsistemas, módulos y comportamientos técnicos.

## Lo que NO haces
- No generas nuevas características (ya están aprobadas).
- No modificas el Discovery (es inmutable en esta fase).
- No generas requisitos para todas las características a la vez — solo para UNA.

## Input que recibes
- Un Documento de Descubrimiento (contexto de negocio).
- UNA característica aprobada (con su código, título, descripción y origen).
- El número de la característica (para formato REQ-X.X).
- Preferencias del usuario (si existen).

## Categorías EARS y su sintaxis

Genera requisitos distribuidos en al menos 4 categorías:

1. **Ubicuo** — Siempre se cumple, sin condiciones.
   Sintaxis: "El sistema debe [comportamiento]".
2. **Basado en Eventos** — Se activa por un evento externo.
   Sintaxis: "CUANDO [evento], el sistema debe [comportamiento]".
3. **Determinado por el Estado** — Se activa mientras persiste un estado.
   Sintaxis: "MIENTRAS [estado], el sistema debe [comportamiento]".
4. **Opcional** — Se activa si una opción está seleccionada.
   Sintaxis: "DONDE [opción], el sistema debe [comportamiento]".
5. **Respuesta ante Comportamiento no Deseado** — Previene o mitiga fallos.
   Sintaxis: "SI [condición no deseada], el sistema debe [comportamiento de mitigación]".
6. **Complejo** — Combina estado y evento.
   Sintaxis: "MIENTRAS [estado] Y CUANDO [evento], el sistema debe [comportamiento]".

## Seis campos de cada requisito

1. **code** — Identificador REQ-X.Y donde X es el número de característica e Y el correlativo.
2. **title** — Título breve de 3 a 6 palabras que resume el propósito del requisito.
   Ejemplo: "Asignación de turnos estándar", "Rechazo de turnos excedidos".
3. **pattern** — Una de las 6 categorías: Ubicuo, Basado en eventos, Determinado por estado,
   Opcional, Comportamiento no deseado, Complejo.
4. **statement** — Oración completa en sintaxis EARS. Es el enunciado del requisito.
5. **origin** — Justificación del requisito y su cadena de derivación hacia la
   característica (C0X) y las secciones del Discovery que lo fundamentan.
   Ejemplo: "Garantiza consistencia en la presentación de valores. Se deriva de C01 y Reglas de negocio."
6. **acceptance_criteria** — Mínimo 2 criterios verificables. Cada criterio tiene:
   - **scenario**: título breve del escenario.
   - **given** (Dado): contexto inicial.
   - **when** (Cuando): acción concreta del usuario.
   - **then** (Entonces): resultado esperado.

## Formato de salida (JSON)

```json
{
  "requirements": [
    {
      "code": "REQ-1.1",
      "title": "Presentación de montos con dos decimales",
      "pattern": "Ubicuo",
      "statement": "El sistema debe presentar todos los montos con exactamente dos decimales",
      "origin": "Garantiza consistencia visual. Se deriva de C01 y Reglas de negocio.",
      "acceptance_criteria": [
        {
          "scenario": "Montos en pantalla de balance",
          "given": "el usuario se encuentra en la pantalla principal del grupo",
          "when": "hace clic en la pestaña Balance",
          "then": "todos los montos aparecen formateados con dos decimales y el símbolo de la moneda del grupo"
        },
        {
          "scenario": "Montos en detalle de un gasto",
          "given": "el usuario se encuentra en el listado de gastos del grupo",
          "when": "hace clic en un gasto registrado para ver su detalle",
          "then": "cada cuota individual aparece con dos decimales y la moneda del grupo"
        }
      ]
    }
  ]
}
```

## Guardrails (obligatorio)

- OBLIGATORIO: al menos 3 requisitos y máximo 15 por feature.
- OBLIGATORIO: al menos 4 categorías EARS diferentes por feature.
- OBLIGATORIO: cada requisito con al menos 2 criterios de aceptación.
- OBLIGATORIO: cada criterio con su scenario, given, when y then completos.
- PROHIBIDO: requisitos ambiguos ("el sistema funcionará bien", "será rápido").
- PROHIBIDO: requisitos duplicados o contradictorios.
- Todo en español con tildes correctas.
- Los criterios de aceptación describen interacciones concretas (clic en botón,
  ingreso de valor, selección de opción).

## Auto-validación (antes de responder)

1. Cada requisito sigue exactamente la sintaxis EARS de su categoría.
2. Cada requisito tiene al menos 2 criterios de aceptación con scenario, given, when y then.
3. No hay requisitos duplicados ni contradictorios.
4. Los criterios de aceptación describen interacciones funcionales concretas.
5. La numeración es REQ-X.Y consistente.
6. Al menos 4 categorías EARS están representadas.
7. El campo origin traza correctamente a la característica y las secciones del Discovery.
"""


class EARSMode:
    def __init__(self) -> None:
        self._feature_id: FeatureId = FeatureId("")
        self._feature_number: int = 0

    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.REQUISITOS

    @property
    def temperature(self) -> float:
        return 0.3

    @property
    def max_tokens(self) -> int:
        return 8192

    @property
    def output_type(self) -> type[BaseModel]:
        from kosmo.contracts.pipeline.phase_outputs import EARSSet

        return EARSSet

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
                description="Rúbrica de calidad de requisitos EARS",
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
                name="validate_ears_software_level",
                description="Valida estructura, criterios de aceptación y categorías EARS a nivel de software",
                parameters={
                    "type": "object",
                    "properties": {
                        "requirements": {
                            "type": "array",
                            "description": "Lista de requisitos a validar",
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
        parts.append(f"- **Código**: {context.feature.display_id}\n")
        parts.append(f"- **Título**: {context.feature.title}\n")
        parts.append(f"- **Descripción**: {context.feature.description}\n")
        parts.append(f"- **Origen**: {context.feature.origin}\n")
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
            software_result = validate_ears_software_level(requirements)

            all_errors = syntax_result.errors + quality_result.errors + software_result.errors
            all_warnings = syntax_result.warnings + quality_result.warnings + software_result.warnings

            return ValidationResult(
                is_valid=len(all_errors) == 0,
                errors=all_errors,
                warnings=all_warnings,
            )

        return ValidationResult(is_valid=False, errors=["Formato de salida no reconocido"])

    def build_validation_feedback(self, errors: list[str]) -> str:
        error_list = "\n".join(f"- {e}" for e in errors)
        return (
            "## Feedback de validacion\n\n"
            f"Los requisitos generados tienen los siguientes problemas:\n\n{error_list}\n\n"
            "Corrige estos problemas y genera los requisitos nuevamente."
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
            f"Los requisitos generados tienen los siguientes problemas:\n\n"
            f"{error_list}\n\n"
            f"Corrige estos problemas y genera los requisitos nuevamente."
        )

    def build_output(
        self,
        raw_output: Any,
        validation_result: ValidationResult,
        metadata: GenerationMetadata,
    ) -> EARSPhaseOutput:
        from kosmo.contracts.sdd.ears import EARSRequirement
        from kosmo.domain.sdd.id_generator import IdGenerator

        reqs_data = self._extract_requirements_list(raw_output)
        requirements: list[EARSRequirement] = []

        for i, item in enumerate(reqs_data, start=1):
            pattern_str = item.get("pattern", "Ubicuo")  # type: ignore[reportUnknownMemberType]
            try:
                pattern = EARSPattern(str(pattern_str))  # type: ignore[reportUnknownArgumentType]
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
                                scenario=str(ac_dict.get("scenario", "")),
                                given=str(ac_dict.get("given", "")),
                                when=str(ac_dict.get("when", "")),
                                then=str(ac_dict.get("then", "")),
                            )
                        )

            requirements.append(
                EARSRequirement(
                    id=RequirementId(IdGenerator.generate("requirement")),
                    feature_id=self._feature_id,
                    feature_number=self._feature_number,
                    requirement_number=i,
                    title=str(item.get("title", "")),  # type: ignore[reportUnknownArgumentType]
                    pattern=pattern,
                    statement=str(item.get("statement", "")),  # type: ignore[reportUnknownArgumentType]
                    origin=str(item.get("origin", "")),  # type: ignore[reportUnknownArgumentType]
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
            if not (hasattr(r, "display_id") and hasattr(r, "statement")):
                continue

            title = getattr(r, "title", "")
            pattern_display = str(r.pattern) if hasattr(r, "pattern") else ""
            statement = r.statement.strip()
            display_id = r.display_id

            block = f"### {display_id} {title}\n\n"
            block += f"**{pattern_display}**\n\n"
            block += f"{statement}\n"

            if hasattr(r, "acceptance_criteria") and r.acceptance_criteria:
                block += "\n**Criterios de Aceptación**\n\n"
                for ac in r.acceptance_criteria:
                    scenario = getattr(ac, "scenario", "")
                    given = getattr(ac, "given", "")
                    when = getattr(ac, "when", "")
                    then = getattr(ac, "then", "")

                    block += f"**Escenario: {scenario}**\n\n"
                    block += f"- **Dado** que {given}\n"
                    block += f"- **Cuando** {when}\n"
                    block += f"- **Entonces** {then}\n\n"

            blocks.append(block.strip())

        return "\n\n---\n\n".join(blocks).strip()
