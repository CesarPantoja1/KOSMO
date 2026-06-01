from datetime import UTC, datetime

from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.sdd.document import DocumentResponse, RichTextDocument, SectionHeading
from kosmo.contracts.sdd.errors import DocumentNotFoundError, ProjectNotFoundError
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import ProjectRepository, SpecRepository
from kosmo.domain.agents.discovery_writer.service import generate_discovery
from kosmo.domain.sdd.document_converters import (
    document_to_markdown,
    extract_sections,
)


class RegenerateDiscoveryUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        spec_repo: SpecRepository,
        llm_client: LLMClient,
    ) -> None:
        self._project_repo = project_repo
        self._spec_repo = spec_repo
        self._llm_client = llm_client

    async def execute(self, project_id: ProjectId) -> DocumentResponse:
        project = await self._project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(str(project_id))

        current_doc = await self._project_repo.get_discovery_document(project_id)
        if current_doc is None:
            raise DocumentNotFoundError("proyecto", str(project_id))

        current_markdown = document_to_markdown(current_doc)
        structured, new_tree = await generate_discovery(
            project_description=project.description,
            constitution=None,
            llm_client=self._llm_client,
            optional_context=("Documento actual (Markdown):\n\n" + current_markdown),
        )

        await self._project_repo.update_discovery_document(project_id, new_tree)

        specs = await self._spec_repo.list_by_project(project_id)
        if specs:
            spec = specs[0]
            spec.discovery = structured
            await self._spec_repo.update(spec)

        secciones_raw = extract_sections(new_tree)
        secciones = [SectionHeading(**s) for s in secciones_raw]

        return DocumentResponse(
            document=RichTextDocument(**new_tree),
            sections=secciones,
            updated_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )
