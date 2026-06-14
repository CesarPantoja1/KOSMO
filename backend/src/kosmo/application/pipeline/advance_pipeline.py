from __future__ import annotations

from kosmo.contracts.pipeline.orchestrator_ports import AgentOrchestrator
from kosmo.contracts.pipeline.pipeline_ports import PipelineRepository
from kosmo.contracts.pipeline.pipeline_state import KOSMOPipelineState
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId


class AdvancePipelineUseCase:
    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        pipeline_repo: PipelineRepository,
    ) -> None:
        self._orchestrator = orchestrator
        self._pipeline_repo = pipeline_repo

    async def execute(
        self,
        project_id: ProjectId,
        target_phase: SpecPhase,
    ) -> KOSMOPipelineState:
        state = await self._pipeline_repo.get(project_id)
        if state is None:
            raise ValueError(f"No se encontro el pipeline para el proyecto {project_id}")

        state = await self._orchestrator.advance_pipeline(state, target_phase)
        state = await self._pipeline_repo.save(state)
        return state
