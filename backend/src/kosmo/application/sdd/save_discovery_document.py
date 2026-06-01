from datetime import UTC, datetime

from kosmo.contracts.sdd.discovery import DiscoveryDocument
from kosmo.contracts.sdd.document import DocumentResponse, RichTextDocument, SectionHeading
from kosmo.contracts.sdd.errors import DocumentValidationError
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import ProjectRepository, SpecRepository
from kosmo.domain.sdd.document_converters import (
    extract_discovery_from_document,
    extract_sections,
    validate_document_structure,
)


class SaveDiscoveryDocumentUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        spec_repo: SpecRepository,
    ) -> None:
        self._project_repo = project_repo
        self._spec_repo = spec_repo

    async def execute(self, project_id: ProjectId, document: dict) -> DocumentResponse:
        hallazgos = validate_document_structure(document)
        if hallazgos:
            raise DocumentValidationError(hallazgos)

        await self._project_repo.update_discovery_document(project_id, document)

        discovery_dict = extract_discovery_from_document(document)
        discovery = DiscoveryDocument(**discovery_dict)

        specs = await self._spec_repo.list_by_project(project_id)
        if specs:
            spec = specs[0]
            spec.discovery = discovery
            await self._spec_repo.update(spec)

        secciones_raw = extract_sections(document)
        secciones = [SectionHeading(**s) for s in secciones_raw]

        return DocumentResponse(
            document=RichTextDocument(**document),
            sections=secciones,
            updated_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )
