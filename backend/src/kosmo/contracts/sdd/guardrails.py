from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GuardrailViolation:
    message: str


@dataclass
class GuardrailResult:
    passed: bool = True
    violations: list[GuardrailViolation] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]


DISCOVERY_SECTIONS: list[str] = []
PROHIBITED_TERMS: list[str] = []
