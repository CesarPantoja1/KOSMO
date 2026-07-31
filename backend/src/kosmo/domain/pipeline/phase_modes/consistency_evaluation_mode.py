from __future__ import annotations

from typing import Any

from kosmo.contracts.pipeline.consistency_phase_context import ConsistencyPhaseContext
from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_outputs import (
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase

_CONSISTENCY_SYSTEM_PROMPT = (
    "Eres un analista de trazabilidad entre fases de un proceso de desarrollo de producto. "
    "Tu tarea es evaluar si los CAMBIOS APLICADOS en una fase origen afectan (dejan desactualizados) "
    "a los ARTEFACTOS de una fase destino.\n\n"
    "REGLAS:\n"
    "- Responde siempre unicamente con el JSON especificado.\n"
    "- Analiza cada artefacto downstream contra cada cambio aplicado.\n"
    "- Un artefacto esta afectado si el cambio modifica un concepto del que el artefacto depende "
    "o hereda. Por ejemplo: un cambio en la Vision del producto afecta caracteristicas que la implementan; "
    "un cambio en una caracteristica afecta requisitos que la detallan.\n"
    "- Si no hay relacion entre el cambio y el artefacto, NO lo incluyas como afectado.\n"
    "- Si el cambio no tiene impacto detectable en ningun artefacto, devuelve lista vacia.\n\n"
    "FORMATO DE SALIDA (JSON):\n"
    "{\n"
    '  "affected_artifact_ids": ["<id1>", "<id2>", ...],\n'
    '  "rationale": "<explicacion breve de por que los artefactos estan afectados>"\n'
    "}\n"
)


class ConsistencyEvaluationMode:
    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.DESCUBRIMIENTO

    @property
    def temperature(self) -> float:
        return 0.3

    @property
    def max_tokens(self) -> int:
        return 2048

    @property
    def output_type(self) -> type[Any]:
        return dict

    @property
    def system_prompt(self) -> str:
        return _CONSISTENCY_SYSTEM_PROMPT

    @property
    def available_tools(self) -> list[ToolDefinition]:
        return []

    def build_user_prompt(self, context: ConsistencyPhaseContext) -> str:
        changes_text = "\n".join(
            f"- [{c.section}] {c.description}\n  Antes: {c.diff.before[:200]}\n  Despues: {c.diff.after[:200]}"
            for c in context.applied_changes
        )
        artifacts_text = "\n".join(
            f"- [{a.artifact_type}] id={a.artifact_id}, titulo=\"{a.title}\", descripcion=\"{a.description[:200]}\""
            for a in context.downstream_artifacts
        )
        return (
            f"## Fase origen: {context.source_phase.value}\n"
            f"## Fase destino: {context.target_phase.value}\n\n"
            f"### Cambios aplicados en la fase origen:\n{changes_text}\n\n"
            f"### Artefactos actuales en la fase destino:\n{artifacts_text}\n\n"
            "Determina cuales de estos artefactos quedan desactualizados por los cambios. "
            "Responde en el formato JSON especificado."
        )

    def validate_output(self, output: Any, *, context: Any = None) -> ValidationResult:  # noqa: ARG002
        errors: list[str] = []
        if not isinstance(output, dict):
            errors.append("El output debe ser un dict (JSON).")
            return ValidationResult(is_valid=False, errors=errors)
        if "affected_artifact_ids" not in output:
            errors.append("Falta el campo 'affected_artifact_ids' en la respuesta.")
        elif not isinstance(output["affected_artifact_ids"], list):
            errors.append("El campo 'affected_artifact_ids' debe ser una lista.")
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
