from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel

from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_contexts import ModeloPhaseContext
from kosmo.contracts.pipeline.phase_outputs import (
    GenerationMetadata,
    ModeloPhaseOutput,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.domain.sdd.validators.activity_diagram_validator import validate_activity_diagram_syntax

_MODELO_SYSTEM_PROMPT = """Eres un arquitecto de software experto en modelado UML,
específicamente en diagramas de actividad con carriles (swimlanes).
Tu ÚNICA responsabilidad es generar el código PlantUML de un diagrama de actividad
organizado por carriles/actores que representan a los participantes o componentes del sistema,
basado en un conjunto de requisitos EARS para una característica específica.

## Tu rol
- Traduces requisitos textuales (EARS) en flujos de control visuales estructurados por carriles.
- CADA diagrama DEBE utilizar carriles (swimlanes) en la sintaxis de PlantUML:
  `|NombreDelCarril|` o `|#color|NombreDelCarril|`.
- Identifica los actores y componentes clave que participan en la característica
  (ej. `|#pink|Usuario|`, `|#lightgray|Sistema|`, `|#lightblue|Base_de_Datos|`).
- El diagrama debe mostrar el flujo principal (Happy Path), caminos alternativos y manejo de errores.
- Utilizas la notación PlantUML para diagramas de actividad (`@startuml` ... `@enduml`).
- Debes incluir nodos de inicio (`start`) y fin (`stop` o `end`).
- Debes utilizar condicionales (`if`, `else`, `elseif`, `endif`) de PlantUML cuando el flujo lo requiera.

## Input que recibes
- El ID de la característica.
- Los requisitos EARS en formato Markdown.
- Preferencias del usuario (si existen).

## Reglas de Sintaxis PlantUML con Carriles (Swimlanes)
- Comienza siempre con `@startuml` y termina con `@enduml`.
- Define y cambia de carril usando la sintaxis `|NombreCarril|` o `|#Color|NombreCarril|`.
- Coloca `start` al inicio del primer carril que dispara la acción.
- Las acciones se asignan al carril activo actual usando `:Acción a realizar;`.
- Puedes personalizar o dar color a los carriles con `|#pink|Actor|`, `|#lightgray|Sistema|`, etc.
- Ejemplo con condicionales y cambios de carril:
  ```plantuml
  |#pink|Usuario|
  start
  if (¿Condición?) is (sí) then
    :**acción red**; <<#pink>>
    :Acción 1;
  else (no)
    |#lightgray|Sistema|
    :**acción not red**; <<#lightgray>>
    :Acción 2;
  endif
  |#lightblue|Siguiente_Actor|
  :Acción 3;
  stop
  ```

## Ejemplo de Salida (Formato JSON)

```json
{
  "diagram_syntax": "@startuml\\n|#pink|Usuario|\\nstart\\n:Pedir;\\n|#lightgray|Sistema|\\n:Validar;\\nstop\\n@enduml"
}
```

## Guardrails (Obligatorio)
- OBLIGATORIO: La respuesta DEBE ser un JSON válido con la propiedad `diagram_syntax`.
- OBLIGATORIO: El valor de `diagram_syntax` DEBE utilizar CARRILES/SWIMLANES (`|NombreCarril|`)
  para separar las acciones según el actor o sistema responsable.
- OBLIGATORIO: El valor de `diagram_syntax` DEBE contener el texto completo de PlantUML,
  escapando correctamente los saltos de línea con `\\n` dentro del JSON.
- OBLIGATORIO: El diagrama debe representar de forma precisa la lógica descrita en los requisitos EARS.
- PROHIBIDO: Inventar flujos que no estén descritos en los requisitos EARS.
"""

class ModeloMode:
    def __init__(self) -> None:
        self._feature_id: FeatureId = FeatureId("")

    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.MODELO

    @property
    def temperature(self) -> float:
        return 0.2

    @property
    def max_tokens(self) -> int:
        return 4096

    @property
    def output_type(self) -> type[BaseModel]:
        from kosmo.contracts.pipeline.phase_outputs import DiagramSpec

        return DiagramSpec

    @property
    def system_prompt(self) -> str:
        return _MODELO_SYSTEM_PROMPT

    @property
    def available_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="validate_activity_diagram_syntax",
                description="Verifica que la sintaxis PlantUML del diagrama de actividad sea válida.",
                parameters={
                    "type": "object",
                    "properties": {
                        "diagram": {
                            "type": "string",
                            "description": "Código fuente PlantUML del diagrama."
                        }
                    },
                    "required": ["diagram"],
                },
            )
        ]

    def build_user_prompt(self, context: ModeloPhaseContext) -> str:
        self._feature_id = context.feature_id

        parts = [f"## Característica ID: {context.feature_id}\n\n"]
        parts.append("## Requisitos EARS\n\n")
        parts.append(context.ears_requirements)

        if context.user_preferences:
            prefs = "\n".join(f"- {p.rule_text}" for p in context.user_preferences)
            parts.append(f"\n\n## Preferencias del usuario\n\n{prefs}")

        return "".join(parts)

    def validate_output(self, output: Any) -> ValidationResult:
        if isinstance(output, dict) and "diagram_syntax" in output:
            diagram = str(cast(object, output["diagram_syntax"]))
            return validate_activity_diagram_syntax(diagram)

        return ValidationResult(
            is_valid=False,
            errors=["Formato de salida no reconocido. Se esperaba un JSON con 'diagram_syntax'."],
        )

    def build_validation_feedback(self, errors: list[str]) -> str:
        error_list = "\n".join(f"- {e}" for e in errors)
        return (
            "## Feedback de validacion\n\n"
            f"El diagrama generado tiene los siguientes problemas:\n\n{error_list}\n\n"
            "Corrige estos problemas y genera el diagrama nuevamente."
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
            f"El diagrama generado tiene los siguientes problemas:\n\n"
            f"{error_list}\n\n"
            f"Corrige estos problemas y genera el diagrama nuevamente."
        )

    def build_output(
        self,
        raw_output: Any,
        validation_result: ValidationResult,
        metadata: GenerationMetadata,
    ) -> ModeloPhaseOutput:

        diagram_syntax = ""
        if isinstance(raw_output, dict) and "diagram_syntax" in raw_output:
            diagram_syntax = str(cast(object, raw_output["diagram_syntax"]))

        return ModeloPhaseOutput(
            feature_id=self._feature_id,
            diagram_syntax=diagram_syntax,
            validation_result=validation_result,
            generation_metadata=metadata,
        )
