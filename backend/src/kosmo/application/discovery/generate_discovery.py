from __future__ import annotations

from kosmo.contracts.pipeline.phase_outputs import DiscoveryPhaseOutput
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository, ProjectRepository
from kosmo.domain.pipeline.context_builder import ContextBuilder
from kosmo.domain.pipeline.kosmo_agent import KOSMOAgent


class GenerateDiscoveryUseCase:
    def __init__(
        self,
        agent: KOSMOAgent,
        context_builder: ContextBuilder,
        project_repo: ProjectRepository,
        document_repo: DocumentRepository,
    ) -> None:
        self._agent = agent
        self._context_builder = context_builder
        self._project_repo = project_repo
        self._document_repo = document_repo

    async def execute(
        self,
        project_id: ProjectId,
    ) -> DiscoveryPhaseOutput:
        project = await self._project_repo.by_id(project_id)
        if project is None:
            raise ValueError(f"No se encontro el proyecto {project_id}")

        await self._project_repo.update_phase(project_id, SpecPhase.DESCUBRIMIENTO)

        context = await self._context_builder.build_context(project_id, SpecPhase.DESCUBRIMIENTO)

        output = await self._agent.execute(SpecPhase.DESCUBRIMIENTO, context)

        if not isinstance(output, DiscoveryPhaseOutput):
            raise ValueError("El agente no genero un output de discovery")

        await self._document_repo.save_discovery(project_id, output.discovery_document)

        return output
