from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawIdea:
    text: str
    optional_context: str | None = None
