from __future__ import annotations

from typing import TYPE_CHECKING

from kosmo.contracts.pipeline.phase_errors import PhaseTransitionError
from kosmo.contracts.pipeline.phase_outputs import (
    DiscoveryPhaseOutput,
    EARSPhaseOutput,
    FeaturesPhaseOutput,
)
from kosmo.contracts.pipeline.pipeline_state import (
    KOSMOPipelineState,
    PhaseTransitionRecord,
)
from kosmo.contracts.sdd.document import FeatureStatus, SpecPhase

if TYPE_CHECKING:
    from kosmo.domain.pipeline.kosmo_agent import KOSMOAgent

_PHASE_ORDER: list[SpecPhase] = [
    SpecPhase.DESCUBRIMIENTO,
    SpecPhase.CARACTERISTICAS,
    SpecPhase.REQUISITOS,
]


class SequentialOrchestrator:
    def __init__(self, agent: KOSMOAgent | None = None) -> None:
        self._agent = agent

    def can_advance(
        self,
        state: KOSMOPipelineState,
        target_phase: SpecPhase,
    ) -> bool:
        try:
            self._validate_transition(state, target_phase)
            return True
        except PhaseTransitionError:
            return False

    async def execute_phase(
        self,
        pipeline_state: KOSMOPipelineState,
        _phase: SpecPhase,
    ) -> KOSMOPipelineState:
        if self._agent is not None:
            output = await self._agent.execute(pipeline_state)
            self._attach_output(pipeline_state, output)
            pipeline_state.updated_at = _utc_now()
        return pipeline_state

    async def advance_pipeline(
        self,
        pipeline_state: KOSMOPipelineState,
        target_phase: SpecPhase,
    ) -> KOSMOPipelineState:
        self._validate_transition(pipeline_state, target_phase)

        transition = PhaseTransitionRecord(
            from_phase=pipeline_state.current_phase,
            to_phase=target_phase,
            validation_passed=True,
        )
        pipeline_state.phase_history.append(transition)
        pipeline_state.current_phase = target_phase
        pipeline_state.updated_at = _utc_now()

        return pipeline_state

    def _attach_output(
        self,
        state: KOSMOPipelineState,
        output: object,
    ) -> None:
        if isinstance(output, DiscoveryPhaseOutput):
            state.discovery_output = output
        elif isinstance(output, FeaturesPhaseOutput):
            state.features_output = output
            state.features = output.features
        elif isinstance(output, EARSPhaseOutput):
            state.ears_outputs[output.feature_id] = output

    def _validate_transition(
        self,
        state: KOSMOPipelineState,
        target_phase: SpecPhase,
    ) -> None:
        current_idx = _PHASE_ORDER.index(state.current_phase)
        target_idx = _PHASE_ORDER.index(target_phase)

        if target_idx <= current_idx and target_phase != state.current_phase:
            raise PhaseTransitionError(
                detail=f"No se puede retroceder de {state.current_phase.value} a {target_phase.value}",
                instance="/pipeline/advance",
            )

        if target_phase == SpecPhase.CARACTERISTICAS:
            if state.discovery_output is None:
                raise PhaseTransitionError(
                    detail="No se puede avanzar a Caracteristicas sin un documento de discovery valido",
                    instance="/pipeline/advance",
                )

        if target_phase == SpecPhase.REQUISITOS:
            approved = [f for f in state.features if f.status == FeatureStatus.aprobada]
            if not approved:
                raise PhaseTransitionError(
                    detail="No se puede avanzar a Requisitos sin al menos una feature aprobada",
                    instance="/pipeline/advance",
                )


def _utc_now():
    from datetime import UTC, datetime

    return datetime.now(UTC)
