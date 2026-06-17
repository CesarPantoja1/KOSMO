from __future__ import annotations

from kosmo.contracts.pipeline.phase_errors import (
    PhaseNotSupportedError,
    PhaseTransitionError,
)
from kosmo.contracts.sdd.document import SpecPhase

# Orden estricto de las fases del pipeline KOSMO
_PHASE_ORDER: list[SpecPhase] = [
    SpecPhase.DESCUBRIMIENTO,
    SpecPhase.CARACTERISTICAS,
    SpecPhase.REQUISITOS,
    SpecPhase.MODELO,
    SpecPhase.IMPLEMENTACION,
]

_PHASE_INDEX: dict[SpecPhase, int] = {
    phase: idx for idx, phase in enumerate(_PHASE_ORDER)
}


class SequentialOrchestrator:
    """Orquestador que impone las reglas de avance secuencial entre fases del pipeline.

    Reglas de transición:
    - Solo se puede avanzar una fase a la vez (no se permiten saltos).
    - No se puede retroceder de fase.
    - La primera ejecución siempre debe comenzar en DESCUBRIMIENTO.
    """

    def validate_transition(
        self,
        current_phase: SpecPhase | None,
        target_phase: SpecPhase,
    ) -> None:
        """Valida que la transición de fase sea permitida.

        Args:
            current_phase: La fase actualmente completada, o None si es la primera fase.
            target_phase: La fase a la que se quiere transicionar.

        Raises:
            PhaseNotSupportedError: Si la fase destino no existe en el pipeline.
            PhaseTransitionError: Si la transición no respeta el orden secuencial.
        """
        if target_phase not in _PHASE_INDEX:
            raise PhaseNotSupportedError(phase=target_phase.value)

        target_idx = _PHASE_INDEX[target_phase]

        # Primera ejecución: solo se puede comenzar en DESCUBRIMIENTO
        if current_phase is None:
            if target_idx != 0:
                raise PhaseTransitionError(
                    detail=(
                        f"La primera fase debe ser '{_PHASE_ORDER[0].value}', "
                        f"no '{target_phase.value}'."
                    )
                )
            return

        if current_phase not in _PHASE_INDEX:
            raise PhaseNotSupportedError(phase=current_phase.value)

        current_idx = _PHASE_INDEX[current_phase]

        # No se puede retroceder
        if target_idx <= current_idx:
            raise PhaseTransitionError(
                detail=(
                    f"No se puede retroceder de la fase '{current_phase.value}' "
                    f"a la fase '{target_phase.value}'."
                )
            )

        # Solo se puede avanzar una fase a la vez
        if target_idx != current_idx + 1:
            expected_next = _PHASE_ORDER[current_idx + 1].value
            raise PhaseTransitionError(
                detail=(
                    f"Transición inválida: desde '{current_phase.value}' "
                    f"solo se puede avanzar a '{expected_next}', "
                    f"no a '{target_phase.value}'."
                )
            )

    def next_phase(self, current_phase: SpecPhase) -> SpecPhase | None:
        """Retorna la siguiente fase en el pipeline, o None si es la última.

        Args:
            current_phase: La fase actual del pipeline.

        Returns:
            La siguiente SpecPhase, o None si no hay más fases.

        Raises:
            PhaseNotSupportedError: Si la fase actual no existe en el pipeline.
        """
        if current_phase not in _PHASE_INDEX:
            raise PhaseNotSupportedError(phase=current_phase.value)

        current_idx = _PHASE_INDEX[current_phase]
        next_idx = current_idx + 1

        if next_idx >= len(_PHASE_ORDER):
            return None

        return _PHASE_ORDER[next_idx]

    @property
    def phases(self) -> list[SpecPhase]:
        """Retorna la lista ordenada de todas las fases del pipeline."""
        return list(_PHASE_ORDER)
