from datetime import UTC, datetime

from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.memory.repositories import UserPreferenceRepository
from kosmo.contracts.sdd.document import DocumentResponse, RichTextDocument, SectionHeading
from kosmo.contracts.sdd.document_repository import DocumentRepository
from kosmo.contracts.sdd.errors import DocumentNotFoundError, DocumentValidationError
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import FeatureRepository
from kosmo.domain.sdd.document_converters import (
    extract_sections,
    validate_document_structure,
)


class SaveRequirementsDocumentUseCase:
    def __init__(
        self,
        feature_repo: FeatureRepository,
        preference_repo: UserPreferenceRepository | None = None,
        llm_client: LLMClient | None = None,
        document_repo: DocumentRepository | None = None,
    ) -> None:
        self._feature_repo = feature_repo
        self._preference_repo = preference_repo
        self._llm_client = llm_client
        self._document_repo = document_repo

    async def execute(
        self,
        feature_id: FeatureId,
        document: dict,
        user_id: str = "",
        project_id: str = "",
    ) -> DocumentResponse:
        feature = await self._feature_repo.get(feature_id)
        if feature is None:
            raise DocumentNotFoundError("caracteristica", str(feature_id))

        hallazgos = validate_document_structure(document)
        if hallazgos:
            raise DocumentValidationError(hallazgos)

        original_document = await self._feature_repo.get_requirements_document(feature_id)

        await self._feature_repo.update_requirements_document(feature_id, document)

        if self._document_repo:
            try:
                await self._document_repo.save_view("feature", str(feature_id), document)
            except Exception:
                pass

        if (
            original_document
            and user_id
            and project_id
            and self._preference_repo
            and self._llm_client
            and original_document != document
        ):
            from kosmo.application.memory.learn_from_correction import (
                LearnFromCorrectionUseCase,
            )
            from kosmo.contracts.sdd.ids import ProjectId

            learn_uc = LearnFromCorrectionUseCase(
                preference_repo=self._preference_repo,
                llm_client=self._llm_client,
            )
            await learn_uc.execute(
                user_id=user_id,
                project_id=ProjectId(project_id),
                original_document=original_document,
                corrected_document=document,
                document_type="requirements",
            )

        secciones_raw = extract_sections(document)
        secciones = [SectionHeading(**s) for s in secciones_raw]

        return DocumentResponse(
            document=RichTextDocument(**document),
            sections=secciones,
            updated_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )
