from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.pipeline.phase_detector import detect_phase_mismatch, phase_label


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
    async def execute(self, input_data: ValidatePhaseContextInput) -> ValidatePhaseContextOutput:
        target_phase = detect_phase_mismatch(input_data.content, input_data.current_phase.value)
        if target_phase is None:
            return ValidatePhaseContextOutput(is_valid=True)

        return ValidatePhaseContextOutput(
            is_valid=False,
            redirect_message=(
                f"Este cambio pertenece a la fase de {phase_label(target_phase)}. Ve a esa fase para realizarlo."
            ),
            target_phase=target_phase,
        )
