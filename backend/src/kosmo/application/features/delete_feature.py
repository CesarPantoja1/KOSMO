from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import FeatureRepository


class DeleteFeatureUseCase:
    def __init__(self, feature_repo: FeatureRepository) -> None:
        self._feature_repo = feature_repo

    async def execute(self, feature_id: FeatureId) -> None:
        feature = await self._feature_repo.get(feature_id)
        if feature is None:
            raise FeatureNotFoundError(str(feature_id))

        await self._feature_repo.delete(feature_id)
