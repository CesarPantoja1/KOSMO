from kosmo.contracts.sdd.errors import FeatureNotFoundError, FeatureOperationError
from kosmo.contracts.sdd.feature import Feature, FeatureStatus
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import FeatureRepository
from kosmo.domain.features.status_transitions import validate_feature_status_transition


class ToggleFeatureStatusUseCase:
    def __init__(self, feature_repo: FeatureRepository) -> None:
        self._feature_repo = feature_repo

    async def execute(self, feature_id: FeatureId, target_status: str | None = None) -> Feature:
        feature = await self._feature_repo.get(feature_id)
        if feature is None:
            raise FeatureNotFoundError(str(feature_id))

        if target_status in ("aprobada", "borrador"):
            new_status = FeatureStatus(target_status)
        else:
            new_status = (
                FeatureStatus.APROBADA
                if feature.status == FeatureStatus.BORRADOR
                else FeatureStatus.BORRADOR
            )

        if not validate_feature_status_transition(feature.status, new_status):
            raise FeatureOperationError(
                f"No se puede cambiar el estado de {feature.status.value} a {new_status.value}"
            )

        feature.status = new_status
        await self._feature_repo.update(feature)
        return feature
