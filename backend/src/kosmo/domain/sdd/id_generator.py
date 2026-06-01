from ulid import ULID


class IdGenerator:
    _PREFIXES = {
        "project": "prj",
        "feature": "feat",
        "spec": "spec",
        "task": "tsk",
        "user": "usr",
        "apikey": "apk",
        "audit": "aud",
    }

    @staticmethod
    def generate(entity: str) -> str:
        prefijo = IdGenerator._PREFIXES[entity]
        return f"{prefijo}_{ULID()}"

    @staticmethod
    def extract_timestamp(uid: str) -> float:
        _, raw = uid.split("_", 1)
        return ULID.from_str(raw).timestamp

    @staticmethod
    def extract_prefix(uid: str) -> str:
        return uid.split("_")[0]
