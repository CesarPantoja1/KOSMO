from __future__ import annotations

from kosmo.contracts.pipeline.orchestrator_ports import AgentOrchestrator
from kosmo.contracts.pipeline.phase_outputs import DiscoveryPhaseOutput
from kosmo.contracts.pipeline.pipeline_ports import PipelineRepository
from kosmo.contracts.pipeline.pipeline_state import KOSMOPipelineState
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import PipelineId, ProjectId, UserId
from kosmo.contracts.sdd.repositories import DocumentRepository, ProjectRepository
from kosmo.domain.sdd.id_generator import IdGenerator


class GenerateDiscoveryUseCase:
    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        pipeline_repo: PipelineRepository,
        project_repo: ProjectRepository,
        document_repo: DocumentRepository,
    ) -> None:
        self._orchestrator = orchestrator
        self._pipeline_repo = pipeline_repo
        self._project_repo = project_repo
        self._document_repo = document_repo

    async def execute(
        self,
        project_id: ProjectId,
    ) -> DiscoveryPhaseOutput:
        project = await self._project_repo.by_id(project_id)
        if project is None:
            raise ValueError(f"No se encontro el proyecto {project_id}")

        state = await self._pipeline_repo.get(project_id)
        if state is None:
            state = KOSMOPipelineState(
                project_id=project_id,
                user_id=UserId(project.owner_id),
                pipeline_id=PipelineId(IdGenerator.generate("pipeline")),
            )
            state = await self._pipeline_repo.save(state)

        state.current_phase = SpecPhase.DESCUBRIMIENTO
        state = await self._orchestrator.execute_phase(state, SpecPhase.DESCUBRIMIENTO)
        state = await self._pipeline_repo.save(state)

        if state.discovery_output is None:
            raise ValueError("El agente no genero un output de discovery")

        await self._document_repo.save_discovery(
            project_id, state.discovery_output.discovery_document
        )

        return state.discovery_output
