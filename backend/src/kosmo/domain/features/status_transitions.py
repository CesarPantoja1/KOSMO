from kosmo.contracts.sdd.feature import FeatureStatus

_ALLOWED_TRANSITIONS: dict[FeatureStatus, set[FeatureStatus]] = {
    FeatureStatus.BORRADOR: {FeatureStatus.APROBADA},
    FeatureStatus.APROBADA: {FeatureStatus.BORRADOR},
}


def validate_feature_status_transition(current: FeatureStatus, target: FeatureStatus) -> bool:
    allowed = _ALLOWED_TRANSITIONS.get(current, set())
    return target in allowed
