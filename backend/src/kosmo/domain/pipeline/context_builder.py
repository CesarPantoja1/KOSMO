from __future__ import annotations

from kosmo.contracts.pipeline.phase_contexts import (
    DiscoveryPhaseContext,
    DiscoveryRefinePhaseContext,
)
from kosmo.contracts.pipeline.phase_errors import PhaseTransitionError
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository, ProjectRepository


class ContextBuilder:
    def __init__(
        self,
        document_repo: DocumentRepository,
        project_repo: ProjectRepository,
    ) -> None:
        self._document_repo = document_repo
        self._project_repo = project_repo

    async def build_context(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
    ) -> DiscoveryPhaseContext:
        if phase != SpecPhase.DESCUBRIMIENTO:
            raise PhaseTransitionError(
                detail=f"La fase {phase.value} no esta implementada en el pipeline actual",
                instance=f"/pipeline/phase/{phase.value}",
            )
        return await self._build_discovery_context(project_id)

    async def _build_discovery_context(
        self,
        project_id: ProjectId,
    ) -> DiscoveryPhaseContext:
        project = await self._project_repo.by_id(project_id)
        if project is None:
            raise PhaseTransitionError(
                detail="No se encontro el proyecto para generar el discovery",
                instance="/pipeline/discovery",
            )
        return DiscoveryPhaseContext(
            project_name=project.name,
            project_description=project.description,
        )

    async def build_discovery_refine_context(
        self,
        project_id: ProjectId,
        user_instructions: str,
    ) -> DiscoveryRefinePhaseContext:
        from kosmo.contracts.pipeline.phase_errors import PhaseTransitionError

        current_document = await self._document_repo.get_discovery(project_id)
        if current_document is None:
            raise PhaseTransitionError(
                detail="No existe un documento de descubrimiento previo para refinar.",
                instance="/pipeline/discovery/refine",
            )

        return DiscoveryRefinePhaseContext(
            current_document=current_document,
            user_instructions=user_instructions,
        )
