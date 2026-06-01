from datetime import UTC, datetime

from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.sdd.document import DocumentResponse, RichTextDocument, SectionHeading
from kosmo.contracts.sdd.errors import (
    FeatureNotApprovedError,
    FeatureNotFoundError,
)
from kosmo.contracts.sdd.feature import FeatureStatus
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import FeatureRepository, SpecRepository
from kosmo.domain.agents.requirements_generator.service import generate_feature_requirements
from kosmo.domain.sdd.document_converters import extract_sections


class RegenerateRequirementsUseCase:
    def __init__(
        self,
        feature_repo: FeatureRepository,
        spec_repo: SpecRepository,
        llm_client: LLMClient,
    ) -> None:
        self._feature_repo = feature_repo
        self._spec_repo = spec_repo
        self._llm_client = llm_client

    async def execute(self, feature_id: FeatureId) -> DocumentResponse:
        feature = await self._feature_repo.get(feature_id)
        if feature is None:
            raise FeatureNotFoundError(str(feature_id))

        if feature.status != FeatureStatus.APROBADA:
            raise FeatureNotApprovedError(str(feature_id))

        await self._feature_repo.get_requirements_document(feature_id)

        specs = await self._spec_repo.list_by_project(feature.project_id)
        discovery = specs[0].discovery if specs and specs[0].discovery else None

        structured, new_tree = await generate_feature_requirements(
            feature_title=feature.title,
            feature_description=feature.description,
            discovery=discovery,
            llm_client=self._llm_client,
        )

        await self._feature_repo.update_requirements(feature_id, structured)
        await self._feature_repo.update_requirements_document(feature_id, new_tree)

        secciones_raw = extract_sections(new_tree)
        secciones = [SectionHeading(**s) for s in secciones_raw]

        return DocumentResponse(
            document=RichTextDocument(**new_tree),
            sections=secciones,
            updated_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )
