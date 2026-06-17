from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserPreference:
    id: str
    user_id: str
    rule_text: str
    category: str = "general"
    priority: int = 0