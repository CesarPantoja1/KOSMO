from __future__ import annotations

from typing import Any, cast

from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_contexts import RequirementsRefinePhaseContext
from kosmo.contracts.pipeline.phase_outputs import (
    EARSPhaseOutput,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import FeatureId, RequirementId
from kosmo.domain.pipeline.phase_validators.requirements_refine_validator import (
    validate_refine_input_exists,
)
from kosmo.domain.sdd.output_guardrails import detect_implementation_leaks
from kosmo.domain.sdd.validators.ears_validator import (
    validate_ears_quality,
    validate_ears_syntax,
)

_REQUIREMENTS_REFINE_SYSTEM_PROMPT = """Eres un ingeniero de requisitos experto en la notación EARS.
Recibes una lista de requisitos EARS EXISTENTES para una característica y una instrucción de refinamiento del usuario.
Tu tarea es reescribir la lista de requisitos aplicando EXACTAMENTE lo que pide
la instrucción: agregar, modificar o eliminar requisitos.

REGLAS DE REFINAMIENTO:
- Parte de la lista de requisitos actual tal como está.
- Mantén el formato EARS para todos los requisitos, incluyendo los nuevos o modificados.
- Mantén la coherencia de la numeración (REQ-X.Y) usando el número de característica proporcionado.
- Si el usuario pide eliminar ciertos requisitos, no los devuelvas en el JSON.
- Todo debe mantenerse a nivel de negocio, sin detallar la implementación técnica
  (sin hablar de API, base de datos, backend, etc.).
- Todo en español con tildes correctas.
- No uses formato de historia de usuario.

Categorías EARS y su sintaxis:
1. Ubiquitous: "[El sistema] shall [comportamiento]".
2. Event-Driven: "CUANDO [evento], [el sistema] shall [comportamiento]".
3. State-Driven: "MIENTRAS [estado], [el sistema] shall [comportamiento]".
4. Optional: "DONDE [opción], [el sistema] shall [comportamiento]".
5. Unwanted: "SI [condición no deseada], [el sistema] shall [comportamiento de mitigación]".
6. Complex: "MIENTRAS [estado] Y [evento], [el sistema] shall [comportamiento]".

Formato de salida (JSON):
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
"""


class RequirementsRefineMode:
    def __init__(self) -> None:
        self._feature_id: FeatureId = FeatureId("")
        self._feature_number: int = 0

    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.REQUISITOS

    @property
    def system_prompt(self) -> str:
        return _REQUIREMENTS_REFINE_SYSTEM_PROMPT

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
                            "description": "Lista de requisitos EARS refinados a validar",
                            "items": {"type": "object"},
                        }
                    },
                    "required": ["requirements"],
                },
            ),
        ]

    def build_user_prompt(self, context: RequirementsRefinePhaseContext) -> str:
        self._feature_id = context.feature.id
        self._feature_number = context.feature_number

        val = validate_refine_input_exists(context.current_requirements)
        if not val.is_valid:
            raise ValueError(val.errors[0])

        import json
        from dataclasses import asdict

        parts = ["## Característica actual\n"]
        parts.append(f"- **ID**: {context.feature.display_id}")
        parts.append(f"- **Título**: {context.feature.title}")
        parts.append(f"- **Descripción**: {context.feature.description}\n")

        parts.append("## Requisitos EARS Actuales\n")
        reqs_list = [asdict(r) for r in context.current_requirements]
        parts.append(json.dumps({"requirements": reqs_list}, ensure_ascii=False, indent=2))

        parts.append("\n## Instrucción de refinamiento del usuario\n")
        parts.append(context.user_instructions)

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
            all_warnings = syntax_result.warnings + quality_result.warnings + leaks_result.error_messages

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
            f"Corrige estos problemas y genera los requisitos nuevamente."
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
                [str(t) for t in cast("list[object]", raw_trace)] if isinstance(raw_trace, list) else []
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
                blocks.append(f"### {r.display_id}\n\n{r.source_statement.strip()}")
        return "\n\n".join(blocks).strip()
