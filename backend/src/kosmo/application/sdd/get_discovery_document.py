from kosmo.contracts.sdd.document import DocumentResponse, RichTextDocument, SectionHeading
from kosmo.contracts.sdd.errors import DocumentNotFoundError, ProjectNotFoundError
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import ProjectRepository
from kosmo.domain.sdd.document_converters import extract_sections


class GetDiscoveryDocumentUseCase:
    def __init__(self, project_repo: ProjectRepository) -> None:
        self._project_repo = project_repo

    async def execute(self, project_id: ProjectId) -> DocumentResponse:
        project = await self._project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(str(project_id))

        document = await self._project_repo.get_discovery_document(project_id)
        if document is None:
            raise DocumentNotFoundError("proyecto", str(project_id))

        secciones_raw = extract_sections(document)
        secciones = [SectionHeading(**s) for s in secciones_raw]

        return DocumentResponse(
            document=RichTextDocument(**document),
            sections=secciones,
            updated_at=project.updated_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )
