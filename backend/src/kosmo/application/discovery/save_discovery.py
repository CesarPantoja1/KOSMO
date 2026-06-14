from __future__ import annotations

from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository


class SaveDiscoveryUseCase:
    def __init__(self, document_repo: DocumentRepository) -> None:
        self._document_repo = document_repo

    async def execute(
        self,
        project_id: ProjectId,
        document: RichTextDocument,
    ) -> None:
        await self._document_repo.save_discovery(project_id, document)
