from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.sdd.errors import FeatureNotEditableError, FeatureNotFoundError
from kosmo.contracts.sdd.feature import Feature, FeatureStatus
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import FeatureRepository, ProjectRepository
from kosmo.domain.agents.feature_generator.service import improve_feature_description
from kosmo.domain.sdd.document_converters import document_to_markdown


class ImproveFeatureSuggestionUseCase:
    def __init__(
        self,
        feature_repo: FeatureRepository,
        project_repo: ProjectRepository,
        llm_client: LLMClient,
    ) -> None:
        self._feature_repo = feature_repo
        self._project_repo = project_repo
        self._llm_client = llm_client

    async def execute(self, feature_id: FeatureId) -> Feature:
        feature = await self._feature_repo.get(feature_id)
        if feature is None:
            raise FeatureNotFoundError(str(feature_id))

        if feature.status != FeatureStatus.BORRADOR:
            raise FeatureNotEditableError(str(feature_id), feature.status.value)

        document = await self._project_repo.get_discovery_document(feature.project_id)
        discovery_markdown = document_to_markdown(document) if document else ""

        suggestion = await improve_feature_description(
            feature, discovery_markdown, self._llm_client
        )

        return Feature(
            id=feature.id,
            project_id=feature.project_id,
            title=suggestion.title,
            description=suggestion.description,
            status=feature.status,
            created_at=feature.created_at,
        )
