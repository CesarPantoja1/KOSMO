from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import FeatureRepository
from kosmo.contracts.sdd.requirements_document import RequirementsDocument


class UpdateFeatureRequirementsUseCase:
    def __init__(self, feature_repo: FeatureRepository) -> None:
        self._feature_repo = feature_repo

    async def execute(
        self, feature_id: FeatureId, updates: dict[str, list[dict[str, object]]]
    ) -> tuple[Feature, RequirementsDocument]:
        feature = await self._feature_repo.get(feature_id)
        if feature is None:
            raise FeatureNotFoundError(str(feature_id))

        current = feature.requirements or RequirementsDocument()
        categories = [
            "ubiquitous",
            "event",
            "state",
            "optional",
            "unwanted",
            "complex",
        ]

        for category in categories:
            if category in updates:
                from kosmo.contracts.sdd.ears import EARSRequirement

                new_list = [EARSRequirement.model_validate(r) for r in updates[category]]
                setattr(current, category, new_list)

        await self._feature_repo.update_requirements(feature_id, current)
        feature.requirements = current

        return feature, current
