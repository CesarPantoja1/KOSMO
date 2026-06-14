from __future__ import annotations

from kosmo.contracts.pipeline.orchestrator_ports import AgentOrchestrator
from kosmo.contracts.pipeline.phase_outputs import EARSPhaseOutput
from kosmo.contracts.pipeline.pipeline_ports import PipelineRepository
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.domain.pipeline.context_builder import ContextBuilder


class GenerateEARSUseCase:
    def __init__(
        self,
        agent: AgentOrchestrator,
        context_builder: ContextBuilder,
        orchestrator: AgentOrchestrator,
        pipeline_repo: PipelineRepository,
    ) -> None:
        self._agent = agent
        self._context_builder = context_builder
        self._orchestrator = orchestrator
        self._pipeline_repo = pipeline_repo

    async def execute(
        self,
        project_id: ProjectId,
        feature_id: FeatureId,
    ) -> EARSPhaseOutput:
        state = await self._pipeline_repo.get(project_id)
        if state is None:
            raise ValueError(f"No se encontro el pipeline para el proyecto {project_id}")

        await self._context_builder.build_ears_context_for_feature(state, feature_id)

        state.current_phase = SpecPhase.REQUISITOS
        state = await self._orchestrator.execute_phase(state, SpecPhase.REQUISITOS)
        state = await self._pipeline_repo.save(state)

        feature_output = state.ears_outputs.get(feature_id)
        if feature_output is None:
            raise ValueError(f"El agente no genero requisitos para la feature {feature_id}")

        return feature_output
