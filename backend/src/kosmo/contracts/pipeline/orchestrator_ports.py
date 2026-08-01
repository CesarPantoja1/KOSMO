from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol

from kosmo.contracts.pipeline.consistency_phase_context import ConsistencyPhaseContext
from kosmo.contracts.pipeline.phase_contexts import (
    DiscoveryChatContext,
    DiscoveryPhaseContext,
    EARSPhaseContext,
    FeatureChatContext,
    FeaturesPhaseContext,
    ModeloPhaseContext,
    RequirementChatContext,
    SuggestFeaturesContext,
)
from kosmo.contracts.pipeline.phase_outputs import (
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase

if TYPE_CHECKING:
    from kosmo.contracts.chat import MensajeChat


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)  # type: ignore[reportUnknownVariableType]


@dataclass(frozen=True)
class Skill:
    """Habilidad del agente que encapsula un modo de fase con metadatos.

    Cada skill agrupa un PhaseMode con su nombre, descripcion y fase asociada,
    permitiendo cargar, descargar y resolver habilidades bajo demanda sin
    modificar el nucleo del agente.
    """

    name: str
    description: str
    phase: SpecPhase
    mode: PhaseMode


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    output: Any
    is_error: bool = False
    error_message: str | None = None


@dataclass(frozen=True)
class AgentStep:
    step_number: int
    reasoning: str = ""
    action: str | None = None
    action_input: dict[str, Any] = field(default_factory=dict)  # type: ignore[reportUnknownVariableType]
    observation: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


@dataclass(frozen=True)
class AgentTrace:
    steps: list[AgentStep] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def tool_calls(self) -> int:
        return sum(1 for s in self.steps if s.action is not None)


class PhaseMode(Protocol):
    @property
    def phase_name(self) -> SpecPhase: ...

    @property
    def system_prompt(self) -> str: ...

    @property
    def available_tools(self) -> list[ToolDefinition]: ...

    @property
    def temperature(self) -> float: ...

    @property
    def max_tokens(self) -> int: ...

    @property
    def output_type(self) -> type[Any]: ...

    def build_user_prompt(
        self,
        context: (
            ConsistencyPhaseContext
            | DiscoveryChatContext
            | DiscoveryPhaseContext
            | EARSPhaseContext
            | FeatureChatContext
            | FeaturesPhaseContext
            | ModeloPhaseContext
            | RequirementChatContext
            | SuggestFeaturesContext
        ),
    ) -> str: ...

    def validate_output(self, output: Any, *, context: Any = None) -> ValidationResult: ...

    def build_retry_prompt(
        self,
        original_prompt: str,
        errors: list[str],
        retry_count: int,
    ) -> str: ...

    def build_validation_feedback(self, errors: list[str]) -> str: ...

    def build_output(
        self,
        raw_output: Any,
        validation_result: ValidationResult,
        metadata: GenerationMetadata,
        *,
        context: Any = None,
    ) -> Any: ...


class AgentPort(Protocol):
    async def execute_with_skill(
        self,
        skill_name: str,
        context: Any,
        *,
        project_id: Any | None = None,
        user_instructions: str | None = None,
    ) -> Any: ...

    async def execute_conversation(
        self,
        skill_name: str,
        messages: list[MensajeChat],
        context: Any,
        *,
        project_id: Any | None = None,
    ) -> MensajeChat: ...
