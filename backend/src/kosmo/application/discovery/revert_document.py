from __future__ import annotations

from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository
from kosmo.domain.sdd.document_converters import markdown_to_document


async def revert_to_version(
    document_repo: DocumentRepository,
    project_id: ProjectId,
    version_id: str,
) -> str | None:
    markdown = await document_repo.get_version(version_id)
    if markdown is None:
        return None
    await document_repo.save_discovery(project_id=project_id, document=markdown_to_document(markdown))
    return markdown
