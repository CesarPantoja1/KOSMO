from __future__ import annotations

from kosmo.contracts.pipeline.phase_contexts import DiscoveryChatContext, DiscoveryRefinePhaseContext
from kosmo.contracts.pipeline.phase_errors import PhaseTransitionError
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

    async def build_discovery_refine_context(
        self,
        project_id: ProjectId,
        user_instructions: str,
    ) -> DiscoveryRefinePhaseContext:
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

    async def build_discovery_chat_context(
        self,
        project_id: ProjectId,
    ) -> DiscoveryChatContext:
        current_document = await self._document_repo.get_discovery(project_id)
        if current_document is None:
            raise PhaseTransitionError(
                detail="No existe un documento de descubrimiento para el chat.",
                instance="/pipeline/discovery/chat",
            )

        return DiscoveryChatContext(current_document=current_document)
