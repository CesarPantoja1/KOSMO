import hashlib
import json
from typing import Any

from kosmo.contracts.sdd.constitution import Constitution, FrozenConstitution


def freeze_constitution(constitution: Constitution) -> FrozenConstitution:
    data: dict[str, Any] = {
        "product": constitution.product,
        "tech": constitution.tech,
        "structure": constitution.structure,
    }
    if constitution.custom:
        data["custom"] = constitution.custom.model_dump(exclude_none=True)

    serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
    version_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    return FrozenConstitution(
        product=constitution.product,
        tech=constitution.tech,
        structure=constitution.structure,
        custom=constitution.custom,
        version_hash=version_hash,
    )
