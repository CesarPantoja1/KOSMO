from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import ProjectRepository
from kosmo.domain.agents.feature_generator.service import suggest_feature_from_idea
from kosmo.domain.sdd.document_converters import document_to_markdown


class SuggestFeatureFromIdeaUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        llm_client: LLMClient,
    ) -> None:
        self._project_repo = project_repo
        self._llm_client = llm_client

    async def execute(self, project_id: ProjectId, idea: str) -> Feature:
        project = await self._project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(str(project_id))

        document = await self._project_repo.get_discovery_document(project_id)
        discovery_markdown = document_to_markdown(document) if document else ""

        return await suggest_feature_from_idea(
            idea, project_id, self._llm_client, discovery_markdown=discovery_markdown
        )
