from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from kosmo.contracts.pipeline.phase_contexts import (
    DiscoveryPhaseContext,
    EARSPhaseContext,
    FeaturesPhaseContext,
    SuggestFeaturesContext,
)
from kosmo.contracts.pipeline.phase_outputs import (
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    output: Any
    is_error: bool = False
    error_message: str | None = None


class PhaseMode(Protocol):
    @property
    def phase_name(self) -> SpecPhase: ...

    @property
    def system_prompt(self) -> str: ...

    @property
    def available_tools(self) -> list[ToolDefinition]: ...

    def build_user_prompt(
        self,
        context: DiscoveryPhaseContext
        | FeaturesPhaseContext
        | EARSPhaseContext
        | SuggestFeaturesContext,
    ) -> str: ...

    def validate_output(self, output: Any) -> ValidationResult: ...

    def build_retry_prompt(
        self,
        original_prompt: str,
        errors: list[str],
        retry_count: int,
    ) -> str: ...
