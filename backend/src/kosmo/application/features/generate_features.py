from __future__ import annotations

from kosmo.contracts.pipeline.phase_outputs import FeaturesPhaseOutput
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository
from kosmo.domain.pipeline.context_builder import ContextBuilder
from kosmo.domain.pipeline.kosmo_agent import KOSMOAgent
from kosmo.domain.pipeline.sequential_orchestrator import SequentialOrchestrator


class GenerateFeaturesUseCase:
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
    ) -> FeaturesPhaseOutput:
        await self._orchestrator.validate_transition(project_id, SpecPhase.CARACTERISTICAS)

        context = await self._context_builder.build_context(project_id, SpecPhase.CARACTERISTICAS)

        output = await self._agent.execute(SpecPhase.CARACTERISTICAS, context)

        if not isinstance(output, FeaturesPhaseOutput):
            raise ValueError("El agente no genero un output de caracteristicas")

        for f in output.features:
            f.project_id = project_id
            await self._feature_repo.save(f)

        return output
