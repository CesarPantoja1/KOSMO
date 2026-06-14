from kosmo.contracts.sdd.document import FeatureStatus
from kosmo.contracts.sdd.errors import FeatureNotEditableError

_VALID_TRANSITIONS: dict[FeatureStatus, set[FeatureStatus]] = {
    FeatureStatus.borrador: {FeatureStatus.aprobada},
    FeatureStatus.aprobada: set(),
}


def can_transition(current: FeatureStatus, target: FeatureStatus) -> bool:
    return target in _VALID_TRANSITIONS.get(current, set())


def transition_feature_status(
    current: FeatureStatus,
    target: FeatureStatus,
    feature_id: str = "",
) -> FeatureStatus:
    if not can_transition(current, target):
        raise FeatureNotEditableError(
            feature_id=feature_id,
            reason=f"No se puede transicionar de {current.value} a {target.value}",
        )
    return target
