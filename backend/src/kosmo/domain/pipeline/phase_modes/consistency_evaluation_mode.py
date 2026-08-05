from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from kosmo.contracts.pipeline.consistency_phase_context import ConsistencyPhaseContext
from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_outputs import (
    ConsistencyReport,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase

_CONSISTENCY_SYSTEM_PROMPT = (
    "Eres un analista experto en trazabilidad de requisitos de software. "
    "Tu tarea es analizar CAMBIOS aplicados a un documento de Descubrimiento de producto "
    "y determinar el impacto sobre artefactos de fases posteriores (Caracteristicas, Requisitos, Modelo).\n\n"
    "## REGLAS DE ANALISIS\n\n"
    "1. LEE el documento fuente COMPLETO (seccion 'Documento fuente actual') y cada artefacto downstream.\n"
    "2. Para cada artefacto, determina una UNICA accion:\n"
    '   - "update": el cambio afecta el contenido del artefacto (ej: unidad de medida, alcance, '
    "terminologia, regla de negocio). DEBES sugerir el texto corregido.\n"
    '   - "delete": el concepto del que depende el artefacto fue ELIMINADO del documento fuente. '
    "El artefacto ya no tiene razon de existir.\n"
    '   - "keep": el artefacto NO esta relacionado con ningun cambio. NO lo incluyas en la respuesta.\n\n'
    "3. ANALISIS SEMANTICO: no busques coincidencia literal de palabras. "
    "Si el descubrimiento cambia 'kilogramos' por 'libras', una caracteristica que menciona 'peso' o 'masa' "
    "SI esta afectada aunque no use la palabra exacta.\n"
    "4. Si un cambio es cosmetico (ortografia, formato) y no altera el significado, el artefacto NO esta afectado.\n"
    "5. Si el cambio modifica una regla de negocio o un alcance funcional, TODOS los artefactos que "
    "implementan esa regla estan afectados.\n\n"
    "## EJEMPLOS\n\n"
    "Ejemplo 1 — Cambio de unidad:\n"
    '  Cambio: "peso en kilogramos" → "peso en libras"\n'
    '  Feature "Calculo de peso total" → accion: "update", '
    'razon: "La unidad de medida cambio de kg a lb, la feature debe reflejar libras."\n\n'
    "Ejemplo 2 — Eliminacion de concepto:\n"
    '  Cambio: se elimina la seccion "Gestion de Inventario" del documento fuente\n'
    '  Feature "Control de stock" → accion: "delete", '
    'razon: "El concepto de inventario ya no existe en el descubrimiento."\n\n'
    "Ejemplo 3 — Cambio cosmetico:\n"
    '  Cambio: se corrige una tilde en "Visión"\n'
    '  Feature "Dashboard de metricas" → NO incluir (accion "keep" implicita).\n\n'
    "## FORMATO DE SALIDA (JSON estricto)\n\n"
    "Responde UNICAMENTE con el siguiente JSON, sin markdown ni texto adicional:\n"
    "{\n"
    '  "actions": [\n'
    "    {\n"
    '      "artifact_id": "<id del artefacto>",\n'
    '      "action": "update" | "delete",\n'
    '      "rationale": "<explicacion clara de por que esta afectado, en español>",\n'
    '      "suggested_field": "<nombre del campo a modificar: title, description>",\n'
    '      "suggested_before": "<texto actual que debe cambiar>",\n'
    '      "suggested_after": "<texto sugerido con el cambio aplicado>"\n'
    "    }\n"
    "  ],\n"
    '  "overall_rationale": "<resumen general del analisis en español>"\n'
    "}\n\n"
    "Si ningun artefacto esta afectado, devuelve: "
    '{"actions": [], "overall_rationale": "Ningun artefacto requiere cambios."}'
)
_CONSISTENCY_UPSTREAM_SYSTEM_PROMPT = (
    "Eres un analista experto en trazabilidad de requisitos de software. "
    "Tu tarea es analizar CAMBIOS aplicados a las Características de un producto "
    "y determinar si dichos cambios entran en conflicto o contradicen la Visión, "
    "Alcance o reglas del documento de Descubrimiento (fase upstream).\n\n"
    "## REGLAS DE ANALISIS\n\n"
    "1. LEE el documento fuente COMPLETO (seccion 'Documento fuente actual') correspondiente "
    "al Descubrimiento, y evalúa los cambios introducidos en las Características.\n"
    "2. Para el documento de Descubrimiento, determina una UNICA accion:\n"
    '   - "update": el cambio en las características obliga a actualizar el descubrimiento '
    "(ej: se agregó una característica fuera del alcance original, "
    "y el negocio decide aceptarla ampliando el alcance, o cambia una regla fundamental). "
    "DEBES sugerir el texto corregido.\n"
    '   - "keep": los cambios en las características son consistentes con la Visión y Alcance '
    "actuales, o son detalles de bajo nivel que NO requieren modificar el Descubrimiento "
    "de alto nivel. NO lo incluyas en la respuesta.\n"
    '   - "delete": el concepto del que depende el artefacto fue ELIMINADO. '
    "(Rara vez aplica hacia upstream a menos que todo el proyecto cambie de rumbo radicalmente).\n\n"
    "3. ANALISIS SEMANTICO: Concéntrate en el impacto a nivel de negocio y alcance. "
    "Si una característica agrega un módulo de 'Pagos con Criptomonedas' pero el Descubrimiento "
    "excluía explícitamente esto en el Alcance, esto es una contradicción y requeriría "
    "un 'update' al alcance si se acepta el cambio.\n"
    "4. NO documentes detalles técnicos o de UI en el Descubrimiento.\n\n"
    "## FORMATO DE SALIDA (JSON estricto)\n\n"
    "Responde UNICAMENTE con el siguiente JSON, sin markdown ni texto adicional:\n"
    "{\n"
    '  "actions": [\n'
    "    {\n"
    '      "artifact_id": "<id del documento de descubrimiento>",\n'
    '      "action": "update" | "delete",\n'
    '      "rationale": "<explicacion clara de por que esta afectado, en español>",\n'
    '      "suggested_field": "<nombre del campo a modificar: title, description>",\n'
    '      "suggested_before": "<texto actual que debe cambiar>",\n'
    '      "suggested_after": "<texto sugerido con el cambio aplicado>"\n'
    "    }\n"
    "  ],\n"
    '  "overall_rationale": "<resumen general del analisis en español>"\n'
    "}\n\n"
    "Si el descubrimiento NO requiere cambios, devuelve: "
    '{"actions": [], "overall_rationale": "Los cambios son consistentes con la visión y alcance actual."}'
)


class ConsistencyEvaluationMode:
    def __init__(
        self,
        phase_name: SpecPhase = SpecPhase.DESCUBRIMIENTO,
        system_prompt: str | None = None,
    ) -> None:
        self._phase_name = phase_name
        self._system_prompt = system_prompt or _CONSISTENCY_SYSTEM_PROMPT

    @property
    def phase_name(self) -> SpecPhase:
        return self._phase_name

    @property
    def temperature(self) -> float:
        return 0.5

    @property
    def max_tokens(self) -> int:
        return 16384

    @property
    def output_type(self) -> type[BaseModel]:
        return ConsistencyReport

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @property
    def available_tools(self) -> list[ToolDefinition]:
        return []

    def build_user_prompt(self, context: ConsistencyPhaseContext) -> str:
        changes_text = "\n".join(
            f"### Cambio en '{c.section}'\n"
            f"**Descripcion:** {c.description}\n"
            f"**Antes:**\n{c.diff.before[:15000]}\n"
            f"**Despues:**\n{c.diff.after[:15000]}\n"
            for c in context.applied_changes
        )
        artifacts_text = "\n".join(
            f'- [{a.artifact_type}] id={a.artifact_id}, titulo="{a.title}", descripcion="{a.description[:12000]}"'
            for a in context.downstream_artifacts
        )
        source_doc = context.source_content[:30000] if context.source_content else "(no disponible)"

        return (
            f"## Fase origen: {context.source_phase.value}\n"
            f"## Fase destino: {context.target_phase.value}\n\n"
            f"### Documento fuente actual:\n{source_doc}\n\n"
            f"### Cambios aplicados:\n{changes_text}\n\n"
            f"### Artefactos actuales en la fase destino:\n{artifacts_text}\n\n"
            "Analiza cada artefacto contra los cambios aplicados y el documento fuente actual. "
            "Determina que accion requiere cada uno (update, delete, o keep). "
            "Para acciones 'update', incluye el texto sugerido. "
            "Responde UNICAMENTE en el formato JSON especificado."
        )

    def validate_output(self, output: Any, *, context: Any = None) -> ValidationResult:  # noqa: ARG002
        errors: list[str] = []
        if not isinstance(output, ConsistencyReport):
            errors.append("El output debe ser un ConsistencyReport.")
            return ValidationResult(is_valid=False, errors=errors)
        if output.actions:
            for idx, action in enumerate(output.actions):
                if not action.artifact_id:
                    errors.append(f"actions[{idx}] falta 'artifact_id'.")
                if not action.rationale:
                    errors.append(f"actions[{idx}] falta 'rationale'.")
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def build_validation_feedback(self, errors: list[str]) -> str:
        error_list = "\n".join(f"- {e}" for e in errors)
        return f"## Errores de validacion\n\n{error_list}\n\nCorrige los errores y genera una nueva respuesta."

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
            f"Errores detectados:\n{error_list}\n\n"
            "Genera una nueva respuesta en el formato JSON especificado."
        )

    def build_output(
        self,
        raw_output: Any,
        validation_result: ValidationResult,  # noqa: ARG002
        metadata: GenerationMetadata,  # noqa: ARG002
        *,
        context: Any = None,  # noqa: ARG002
    ) -> Any:
        return raw_output
