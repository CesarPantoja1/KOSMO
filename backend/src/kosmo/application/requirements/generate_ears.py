from __future__ import annotations

from kosmo.contracts.pipeline.phase_outputs import EARSPhaseOutput
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository
from kosmo.domain.pipeline.context_builder import ContextBuilder
from kosmo.domain.pipeline.kosmo_agent import KOSMOAgent
from kosmo.domain.pipeline.sequential_orchestrator import SequentialOrchestrator


class GenerateEARSUseCase:
    def __init__(
        self,
        agent: KOSMOAgent,
        context_builder: ContextBuilder,
        orchestrator: SequentialOrchestrator,
        feature_repo: FeatureRepository,
    ) -> None:
        self._agent = agent
        self._context_builder = context_builder
        self._orchestrator = orchestrator
        self._feature_repo = feature_repo

    async def execute(
        self,
        project_id: ProjectId,
        feature_id: FeatureId,
    ) -> EARSPhaseOutput:
        await self._orchestrator.validate_transition(project_id, SpecPhase.REQUISITOS)

        context = await self._context_builder.build_ears_context_for_feature(project_id, feature_id)

        output = await self._agent.execute(SpecPhase.REQUISITOS, context)

        if not isinstance(output, EARSPhaseOutput):
            raise ValueError("El agente no genero requisitos")

        return output
