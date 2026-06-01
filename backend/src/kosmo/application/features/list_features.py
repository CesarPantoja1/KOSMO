from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository


class ListFeaturesUseCase:
    def __init__(self, feature_repo: FeatureRepository) -> None:
        self._feature_repo = feature_repo

    async def execute(self, project_id: ProjectId) -> list[Feature]:
        return await self._feature_repo.get_by_project(project_id)
