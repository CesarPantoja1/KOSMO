from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository
from kosmo.domain.sdd.id_generator import IdGenerator


class SaveSelectedSuggestionsUseCase:
    def __init__(self, feature_repo: FeatureRepository) -> None:
        self._feature_repo = feature_repo

    async def execute(
        self,
        project_id: ProjectId,
        selected_features: list[dict],
    ) -> list[Feature]:
        saved: list[Feature] = []
        for item in selected_features:
            feature = Feature(
                id=FeatureId(IdGenerator.generate("feature")),
                project_id=project_id,
                title=item["title"],
                description=item["description"],
            )
            await self._feature_repo.add(feature)
            saved.append(feature)
        return saved
