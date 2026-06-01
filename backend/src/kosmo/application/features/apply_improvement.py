from kosmo.contracts.sdd.errors import FeatureNotEditableError, FeatureNotFoundError
from kosmo.contracts.sdd.feature import Feature, FeatureStatus
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import FeatureRepository


class ApplyFeatureImprovementUseCase:
    def __init__(self, feature_repo: FeatureRepository) -> None:
        self._feature_repo = feature_repo

    async def execute(self, feature_id: FeatureId, title: str, description: str) -> Feature:
        feature = await self._feature_repo.get(feature_id)
        if feature is None:
            raise FeatureNotFoundError(str(feature_id))

        if feature.status != FeatureStatus.BORRADOR:
            raise FeatureNotEditableError(str(feature_id), feature.status.value)

        feature.title = title
        feature.description = description
        await self._feature_repo.update(feature)
        return feature
