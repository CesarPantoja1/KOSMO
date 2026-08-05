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
    "agent_memory": "agm_",
    "activity_diagram": "dia_",
    "knowledge_pattern": "kpat_",
    "chat_history": "chh_",
    "chat_message": "msg_",
    "plan_change": "chg_",
    "outbox": "out_",
    "doc_version": "dver_",
    "trace_edge": "ted_",
    "user_pref": "upf_",
}


class IdGenerator:
    @staticmethod
    def generate(entity: str) -> str:
        prefix = _PREFIX_MAP.get(entity)
        if prefix is None:
            raise ValueError(f"Entidad desconocida: {entity}. Valores validos: {sorted(_PREFIX_MAP.keys())}")
        return f"{prefix}{ULID()}"
