from __future__ import annotations

from kosmo.contracts.pipeline.orchestrator_ports import AgentOrchestrator
from kosmo.contracts.pipeline.phase_outputs import SuggestFeaturesOutput
from kosmo.contracts.pipeline.pipeline_ports import PipelineRepository
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.pipeline.context_builder import ContextBuilder


class SuggestFeaturesUseCase:
    def __init__(
        self,
        agent: AgentOrchestrator,
        context_builder: ContextBuilder,
        pipeline_repo: PipelineRepository,
    ) -> None:
        self._agent = agent
        self._context_builder = context_builder
        self._pipeline_repo = pipeline_repo

    async def execute(
        self,
        project_id: ProjectId,
    ) -> SuggestFeaturesOutput:
        state = await self._pipeline_repo.get(project_id)
        if state is None:
            raise ValueError(f"No se encontro el pipeline para el proyecto {project_id}")

        from kosmo.domain.pipeline.kosmo_agent import KOSMOAgent

        if not isinstance(self._agent, KOSMOAgent):
            raise ValueError("El agente debe ser un KOSMOAgent para usar suggest_features")

        output = await self._agent.execute_suggest(state)
        return output
