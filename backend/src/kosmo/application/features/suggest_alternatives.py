from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository, ProjectRepository
from kosmo.domain.agents.feature_generator.service import suggest_alternative_features
from kosmo.domain.sdd.document_converters import document_to_markdown


def _normalize_title(title: str) -> str:
    return title.strip().lower()


class SuggestAlternativeFeaturesUseCase:
    def __init__(
        self,
        feature_repo: FeatureRepository,
        project_repo: ProjectRepository,
        llm_client: LLMClient,
    ) -> None:
        self._feature_repo = feature_repo
        self._project_repo = project_repo
        self._llm_client = llm_client

    async def execute(self, project_id: ProjectId) -> list[Feature]:
        project = await self._project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(str(project_id))

        document = await self._project_repo.get_discovery_document(project_id)
        if document is None:
            return []

        discovery_markdown = document_to_markdown(document)

        existing_features = await self._feature_repo.get_by_project(project_id)
        existing_titles = {_normalize_title(f.title) for f in existing_features}

        suggestions = await suggest_alternative_features(
            project_id, self._llm_client, discovery_markdown=discovery_markdown
        )

        unique = [f for f in suggestions if _normalize_title(f.title) not in existing_titles]

        return unique[:3]
