from __future__ import annotations

from dataclasses import dataclass

import structlog

from kosmo.contracts.sdd.document import SpecPhase

_log = structlog.get_logger(__name__)

_PHASE_KEYWORDS: dict[str, list[str]] = {
    "descubrimiento": [
        "visión", "vision", "negocio", "mercado", "propuesta de valor", "alcance general",
        "actores", "actores del sistema", "metas", "meta del producto", "problema",
        "diferenciador", "modelo de negocio", "estrategia", "objetivo general",
    ],
    "caracteristicas": [
        "característica", "caracteristica", "funcionalidad", "feature", "título", "titulo",
        "origen de la característica", "c01", "c02", "c03", "c04", "c05",
        "acción de usuario", "accion de usuario", "regla de negocio", "descuento",
    ],
    "requisitos": [
        "requisito", "criterio de aceptación", "criterio de aceptacion",
        "dado-cuando-entonces", "ears", "validación", "validacion",
        "especificación técnica", "especificacion tecnica", "req-", "req_",
        "given-when-then", "gwt",
    ],
}

_PHASE_LABELS: dict[str, str] = {
    "descubrimiento": "Descubrimiento",
    "caracteristicas": "Características",
    "requisitos": "Requisitos",
}


@dataclass(frozen=True)
class ValidatePhaseContextInput:
    content: str
    current_phase: SpecPhase


@dataclass(frozen=True)
class ValidatePhaseContextOutput:
    is_valid: bool
    redirect_message: str | None = None
    target_phase: str | None = None


class ValidatePhaseContextUseCase:
    def __init__(self) -> None:
        pass

    async def execute(self, input_data: ValidatePhaseContextInput) -> ValidatePhaseContextOutput:
        content = input_data.content.strip().lower()
        if not content:
            return ValidatePhaseContextOutput(is_valid=True)

        current_phase = input_data.current_phase.value.lower()

        scores: dict[str, int] = {}
        for phase, keywords in _PHASE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in content)
            if score > 0:
                scores[phase] = score

        if not scores:
            return ValidatePhaseContextOutput(is_valid=True)

        best_phase = max(scores, key=lambda k: scores[k])
        if best_phase == current_phase:
            return ValidatePhaseContextOutput(is_valid=True)

        if scores.get(current_phase, 0) >= 2:
            return ValidatePhaseContextOutput(is_valid=True)

        label = _PHASE_LABELS.get(best_phase, best_phase)
        return ValidatePhaseContextOutput(
            is_valid=False,
            redirect_message=f"Este cambio pertenece a la fase de {label}. Ve a esa fase para realizarlo.",
            target_phase=best_phase,
        )
