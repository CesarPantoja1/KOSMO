from datetime import UTC, datetime

from kosmo.contracts.sdd.document import DocumentResponse, RichTextDocument, SectionHeading
from kosmo.contracts.sdd.errors import DocumentNotFoundError, DocumentValidationError
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import FeatureRepository
from kosmo.domain.sdd.document_converters import (
    extract_sections,
    validate_document_structure,
)


class SaveRequirementsDocumentUseCase:
    def __init__(self, feature_repo: FeatureRepository) -> None:
        self._feature_repo = feature_repo

    async def execute(self, feature_id: FeatureId, document: dict) -> DocumentResponse:
        feature = await self._feature_repo.get(feature_id)
        if feature is None:
            raise DocumentNotFoundError("caracteristica", str(feature_id))

        hallazgos = validate_document_structure(document)
        if hallazgos:
            raise DocumentValidationError(hallazgos)

        await self._feature_repo.update_requirements_document(feature_id, document)

        secciones_raw = extract_sections(document)
        secciones = [SectionHeading(**s) for s in secciones_raw]

        return DocumentResponse(
            document=RichTextDocument(**document),
            sections=secciones,
            updated_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )
