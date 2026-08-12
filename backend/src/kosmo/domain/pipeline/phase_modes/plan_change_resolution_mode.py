from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_contexts import PlanChangeResolutionContext
from kosmo.contracts.pipeline.phase_outputs import (
    GenerationMetadata,
    ResolvedSection,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase

_SYSTEM_PROMPT = (
    "Eres un editor experto de documentos markdown.\n\n"
    "Recibes el contenido ACTUAL de una seccion de un documento y una lista "
    "de cambios que el usuario quiere aplicar.\n\n"
    "## REGLAS\n\n"
    "1. Aplica TODOS los cambios de forma consolidada en una sola pasada.\n"
    "2. Los cambios pueden citar texto con redaccion aproximada: identifica el "
    "texto real por su SIGNIFICADO, no por coincidencia literal. Si el texto "
    "original citado ya no aparece exactamente, busca el fragmento equivalente "
    "y aplica la modificacion de todos modos.\n"
    "3. Si un cambio agrega contenido NUEVO, ubicalo como ULTIMO elemento de la "
    "SUBSECCION correcta segun su descripcion y la estructura de la seccion. "
    "Por ejemplo, si la seccion tiene subsecciones 'Incluido' y 'Futuro "
    "potencial', el contenido nuevo va en 'Incluido', NUNCA en 'Futuro "
    "potencial'.\n"
    "4. Si dos cambios se solapan o afectan el mismo texto, fusionalos "
    "coherentemente sin duplicar contenido.\n"
    "5. NO modifiques contenido no afectado por ningun cambio.\n"
    "6. Conserva intactos el heading de la seccion y todos los headings de "
    "subsecciones, con su nivel jerarquico original.\n"
    "7. Escribe en español correcto con todas las tildes.\n"
    "8. Devuelve UNICAMENTE el markdown completo de la seccion reescrita, sin "
    "explicaciones ni texto adicional."
)


class PlanChangeResolutionMode:
    @property
    def requires_enrichment(self) -> bool:
        return False

    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.DESCUBRIMIENTO

    @property
    def temperature(self) -> float:
        return 0.2

    @property
    def max_tokens(self) -> int:
        return 8192

    @property
    def output_type(self) -> type[BaseModel]:
        return ResolvedSection

    @property
    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    @property
    def available_tools(self) -> list[ToolDefinition]:
        return []

    def build_user_prompt(self, context: PlanChangeResolutionContext) -> str:
        changes_text = "\n\n".join(
            f"### Cambio {i + 1}\n"
            f"- Seccion declarada: {c.section or '(no especificada)'}\n"
            f"- Descripcion: {c.description or '(sin descripcion)'}\n"
            f"- Texto original citado (aproximado): "
            f"{c.diff.before[:3000] if c.diff.before else '(contenido nuevo)'}\n"
            f"- Texto nuevo: {c.diff.after[:4000]}"
            for i, c in enumerate(context.changes)
        )
        return (
            f"## Seccion a modificar: {context.section_name}\n\n"
            f"### Contenido ACTUAL de la seccion:\n"
            f"{context.section_markdown}\n\n"
            f"### Cambios solicitados:\n{changes_text}\n\n"
            "Aplica todos los cambios de forma consolidada y devuelve la "
            "seccion completa reescrita en el formato especificado."
        )

    def validate_output(self, output: Any, *, context: Any = None) -> ValidationResult:  # noqa: ARG002
        errors: list[str] = []
        if not isinstance(output, ResolvedSection):
            errors.append("El output debe ser un ResolvedSection.")
            return ValidationResult(is_valid=False, errors=errors)
        if not output.section_markdown.strip():
            errors.append("La seccion reescrita no puede estar vacia.")
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
            "Genera una nueva respuesta en el formato especificado."
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
