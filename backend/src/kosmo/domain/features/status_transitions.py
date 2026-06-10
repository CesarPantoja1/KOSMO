from kosmo.contracts.sdd.errors import FeatureNotApprovedError
from kosmo.contracts.sdd.feature import Feature, FeatureStatus

_ALLOWED_TRANSITIONS: dict[FeatureStatus, set[FeatureStatus]] = {
    FeatureStatus.BORRADOR: {FeatureStatus.APROBADA},
    FeatureStatus.APROBADA: {FeatureStatus.BORRADOR},
}


def validate_feature_status_transition(current: FeatureStatus, target: FeatureStatus) -> bool:
    allowed = _ALLOWED_TRANSITIONS.get(current, set())
    return target in allowed


def validate_requirements_generation_allowed(feature: Feature) -> None:
    if feature.status != FeatureStatus.APROBADA:
        raise FeatureNotApprovedError(str(feature.id))
