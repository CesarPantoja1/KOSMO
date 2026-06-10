from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, Field


def _dict_merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    return {**a, **b}


def _last_wins(a: object, b: object) -> object:
    return b


_MAX_CONCURRENT_LIST_SIZE = 200

_ListT = list[Any]


def _list_merge(a: _ListT, b: _ListT) -> _ListT:
    combined = a + b
    return combined[-_MAX_CONCURRENT_LIST_SIZE:] if len(combined) > _MAX_CONCURRENT_LIST_SIZE else combined

from kosmo.contracts.sdd.discovery import DiscoveryDocument, RawIdea
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.schemas import Scratchpad
from kosmo.contracts.sdd.spec import SpecPhase


class AgentMessage(BaseModel):
    from_agent: str
    to_agent: str
    message_type: str
    content: str
    priority: str = "normal"
    metadata: dict[str, object] = Field(default_factory=dict)


class SupervisorStage(StrEnum):
    CONTEXT = "context"
    GENERATE = "generate"
    EVALUATE = "evaluate"
    DONE = "done"


class CritiqueRecord(BaseModel):
    agent_id: str
    severity: str
    message: str
    field: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ToolCallRecord(BaseModel):
    agent_id: str
    tool_name: str
    params: dict[str, object]
    result: object | None = None
    error: str | None = None
    duration_ms: int | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class KOSMOState(BaseModel):
    """Estado global del grafo de orquestacion multiagente KOSMO.

    Cada nodo valida project_id y user_id via verify_scope().
    Los generadores implementan ciclo ReAct: Thought -> Action -> Observation.
    Todo output al usuario pasa obligatoriamente por critic_evaluator y final_evaluator.
    Los ciclos usan generation_attempts/max_iterations para el pipeline global y
    critic_iteration/max_critic_iterations para el loop generador-critico.

    Campos con reducer Annotated ([list] con operator.add, [dict] con _dict_merge,
    scalares con _last_wins) permiten escritura concurrente desde nodos paralelos
    (Send<3> en CONTEXT, fan-out<3> en CRITICS).
    """

    model_config = {"arbitrary_types_allowed": True}

    project_id: str
    user_id: str

    raw_idea: RawIdea | None = None
    discovery: DiscoveryDocument | None = None
    features: list[Feature] = Field(default_factory=list)
    requirements: list[EARSRequirement] = Field(default_factory=list)

    phase: SpecPhase = SpecPhase.DESCUBRIMIENTO

    shared_scratchpad: Annotated[dict[str, object], _dict_merge] = Field(default_factory=dict)
    agent_outputs: Annotated[dict[str, object], _dict_merge] = Field(default_factory=dict)

    scratchpad: Scratchpad = Field(default_factory=Scratchpad)

    existing_feature_titles: list[str] = Field(default_factory=list)
    existing_feature_ids: list[str] = Field(default_factory=list)

    agent_mailbox: Annotated[dict[str, list[AgentMessage]], _dict_merge] = Field(
        default_factory=dict
    )

    critique_log: Annotated[list[CritiqueRecord], _list_merge] = Field(default_factory=list)
    tool_call_history: Annotated[list[ToolCallRecord], _list_merge] = Field(default_factory=list)

    max_iterations: int = 10
    generation_attempts: int = 0
    critic_iteration: int = 0
    max_critic_iterations: int = 3

    validation_status: Annotated[str | None, _last_wins] = None
    critic_verdict: Annotated[str | None, _last_wins] = None

    current_subtask: str | None = None

    human_input_pending: bool = False
    human_prompt: str | None = None

    supervisor_stage: SupervisorStage = SupervisorStage.CONTEXT
    output_ready: bool = False
    evaluation_summary: dict[str, object] = Field(default_factory=dict)

    errors: Annotated[list[str], _list_merge] = Field(default_factory=list)


SDDState = KOSMOState
