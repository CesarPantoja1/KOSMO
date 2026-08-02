from __future__ import annotations

from typing import Any


def dict_str_keys(d: Any) -> dict[str, Any]:
    if not isinstance(d, dict):
        return {}
    return {k: v for k, v in d.items() if isinstance(k, str)}  # type: ignore[reportUnknownVariableType]
