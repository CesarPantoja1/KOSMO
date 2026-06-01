from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.sdd.errors import FeatureNotApprovedError, FeatureNotFoundError
from kosmo.contracts.sdd.feature import FeatureStatus
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import FeatureRepository, SpecRepository
from kosmo.contracts.sdd.requirements_document import RequirementsDocument
from kosmo.domain.agents.requirements_generator.service import generate_feature_requirements


class GenerateFeatureRequirementsUseCase:
    def __init__(
        self,
        feature_repo: FeatureRepository,
        spec_repo: SpecRepository,
        llm_client: LLMClient,
    ) -> None:
        self._feature_repo = feature_repo
        self._spec_repo = spec_repo
        self._llm_client = llm_client

    async def execute(self, feature_id: FeatureId) -> RequirementsDocument:
        feature = await self._feature_repo.get(feature_id)
        if feature is None:
            raise FeatureNotFoundError(str(feature_id))

        if feature.status != FeatureStatus.APROBADA:
            raise FeatureNotApprovedError(str(feature_id))

        specs = await self._spec_repo.list_by_project(feature.project_id)
        discovery = specs[0].discovery if specs and specs[0].discovery else None

        requirements, document_tree = await generate_feature_requirements(
            feature_title=feature.title,
            feature_description=feature.description,
            discovery=discovery,
            llm_client=self._llm_client,
        )

        await self._feature_repo.update_requirements(feature_id, requirements)
        await self._feature_repo.update_requirements_document(feature_id, document_tree)

        return requirements
