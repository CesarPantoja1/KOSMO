from __future__ import annotations

from datetime import UTC, datetime

from kosmo.contracts.pipeline.pipeline_ports import PipelineRepository
from kosmo.contracts.pipeline.pipeline_state import KOSMOPipelineState
from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository


class SaveDiscoveryUseCase:
    def __init__(
        self,
        pipeline_repo: PipelineRepository,
        document_repo: DocumentRepository,
    ) -> None:
        self._pipeline_repo = pipeline_repo
        self._document_repo = document_repo

    async def execute(
        self,
        project_id: ProjectId,
        document: RichTextDocument,
    ) -> KOSMOPipelineState:
        state = await self._pipeline_repo.get(project_id)
        if state is None:
            raise ValueError(f"No se encontro el pipeline para el proyecto {project_id}")

        state.updated_at = datetime.now(UTC)
        state = await self._pipeline_repo.save(state)

        await self._document_repo.save_discovery(project_id, document)

        return state
