from __future__ import annotations

from ulid import ULID

_PREFIX_MAP: dict[str, str] = {
    "project": "prj_",
    "feature": "feat_",
    "spec": "spec_",
    "task": "tsk_",
    "user": "usr_",
    "apikey": "apk_",
    "audit": "aud_",
    "pipeline": "pipe_",
    "requirement": "req_",
}


class IdGenerator:
    @staticmethod
    def generate(entity: str) -> str:
        prefix = _PREFIX_MAP.get(entity)
        if prefix is None:
            raise ValueError(
                f"Entidad desconocida: {entity}. Valores validos: {sorted(_PREFIX_MAP.keys())}"
            )
        return f"{prefix}{ULID()}"
