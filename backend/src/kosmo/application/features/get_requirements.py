from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import FeatureRepository
from kosmo.contracts.sdd.requirements_document import RequirementsDocument


class GetFeatureRequirementsUseCase:
    def __init__(self, feature_repo: FeatureRepository) -> None:
        self._feature_repo = feature_repo

    async def execute(self, feature_id: FeatureId) -> tuple[Feature, RequirementsDocument]:
        feature = await self._feature_repo.get(feature_id)
        if feature is None:
            raise FeatureNotFoundError(str(feature_id))

        requirements = feature.requirements or RequirementsDocument()
        return feature, requirements
