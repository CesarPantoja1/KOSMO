from datetime import UTC, datetime

from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.memory.repositories import UserPreferenceRepository
from kosmo.contracts.sdd.discovery import DiscoveryDocument
from kosmo.contracts.sdd.document import DocumentResponse, RichTextDocument, SectionHeading
from kosmo.contracts.sdd.document_repository import DocumentRepository
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
        preference_repo: UserPreferenceRepository | None = None,
        llm_client: LLMClient | None = None,
        document_repo: DocumentRepository | None = None,
    ) -> None:
        self._project_repo = project_repo
        self._spec_repo = spec_repo
        self._preference_repo = preference_repo
        self._llm_client = llm_client
        self._document_repo = document_repo

    async def execute(
        self,
        project_id: ProjectId,
        document: dict,
        user_id: str = "",
    ) -> DocumentResponse:
        hallazgos = validate_document_structure(document)
        if hallazgos:
            raise DocumentValidationError(hallazgos)

        original_document = await self._project_repo.get_discovery_document(project_id)

        await self._project_repo.update_discovery_document(project_id, document)

        discovery_dict = extract_discovery_from_document(document)
        discovery = DiscoveryDocument(**discovery_dict)

        if self._document_repo:
            try:
                await self._document_repo.save_clean_discovery(project_id, discovery)
                await self._document_repo.save_view("project", str(project_id), document)
            except Exception:
                pass

        specs = await self._spec_repo.list_by_project(project_id)
        if specs:
            spec = specs[0]
            spec.discovery = discovery
            await self._spec_repo.update(spec)

        if (
            original_document
            and user_id
            and self._preference_repo
            and self._llm_client
            and original_document != document
        ):
            from kosmo.application.memory.learn_from_correction import (
                LearnFromCorrectionUseCase,
            )

            learn_uc = LearnFromCorrectionUseCase(
                preference_repo=self._preference_repo,
                llm_client=self._llm_client,
            )
            await learn_uc.execute(
                user_id=user_id,
                project_id=project_id,
                original_document=original_document,
                corrected_document=document,
                document_type="discovery",
            )

        secciones_raw = extract_sections(document)
        secciones = [SectionHeading(**s) for s in secciones_raw]

        return DocumentResponse(
            document=RichTextDocument(**document),
            sections=secciones,
            updated_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )
