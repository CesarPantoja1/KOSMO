from kosmo.contracts.sdd.document import DocumentResponse, RichTextDocument, SectionHeading
from kosmo.contracts.sdd.errors import DocumentNotFoundError
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import FeatureRepository
from kosmo.domain.sdd.document_converters import extract_sections


class GetRequirementsDocumentUseCase:
    def __init__(self, feature_repo: FeatureRepository) -> None:
        self._feature_repo = feature_repo

    async def execute(self, feature_id: FeatureId) -> DocumentResponse:
        feature = await self._feature_repo.get(feature_id)
        if feature is None:
            raise DocumentNotFoundError("caracteristica", str(feature_id))

        document = await self._feature_repo.get_requirements_document(feature_id)
        if document is None:
            raise DocumentNotFoundError("requisitos", str(feature_id))

        secciones_raw = extract_sections(document)
        secciones = [SectionHeading(**s) for s in secciones_raw]

        return DocumentResponse(
            document=RichTextDocument(**document),
            sections=secciones,
            updated_at=feature.created_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )
