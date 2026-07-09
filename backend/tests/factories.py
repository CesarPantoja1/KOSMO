from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from kosmo.contracts.agent_memory import AgentSession, AgentSessionSummary
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import AgentMemoryId, ProjectId


def a_session_id() -> AgentMemoryId:
    return AgentMemoryId("agm_01KT01FABRICATED01")


def a_project_id() -> ProjectId:
    return ProjectId("prj_01KT01FABRICATED01")


def _a_different_session_id() -> AgentMemoryId:
    from kosmo.domain.agent_memory.session_factory import generate_session_id

    return generate_session_id()


def a_session(
    *,
    session_id: AgentMemoryId | None = None,
    project_id: ProjectId | None = None,
    session_type: str = "generation",
    phase: SpecPhase = SpecPhase.DESCUBRIMIENTO,
    skill_name: str | None = None,
    conversation: list[str] | None = None,
    reasoning_log: list[str] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
    current_iteration: int = 0,
    max_iterations: int = 8,
    is_completed: bool = False,
    output_json: str | None = None,
    validation_is_valid: bool = False,
    validation_errors: int = 0,
    total_llm_calls: int = 0,
    user_instructions: str | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> AgentSession:
    now = datetime.now(UTC)
    return AgentSession(
        session_id=session_id or _a_different_session_id(),
        project_id=project_id or a_project_id(),
        session_type=session_type,
        phase=phase,
        skill_name=skill_name,
        conversation=conversation or [],
        reasoning_log=reasoning_log or [],
        tool_results=tool_results or [],
        current_iteration=current_iteration,
        max_iterations=max_iterations,
        is_completed=is_completed,
        output_json=output_json,
        validation_is_valid=validation_is_valid,
        validation_errors=validation_errors,
        total_llm_calls=total_llm_calls,
        user_instructions=user_instructions,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


def a_session_summary(
    *,
    session_id: AgentMemoryId | None = None,
    project_id: ProjectId | None = None,
    session_type: str = "generation",
    phase: SpecPhase = SpecPhase.DESCUBRIMIENTO,
    skill_name: str | None = None,
    is_completed: bool = False,
    total_llm_calls: int = 0,
    validation_errors: int = 0,
    user_instructions: str | None = None,
    created_at: datetime | None = None,
) -> AgentSessionSummary:
    return AgentSessionSummary(
        session_id=session_id or a_session_id(),
        project_id=project_id or a_project_id(),
        session_type=session_type,
        phase=phase,
        skill_name=skill_name,
        is_completed=is_completed,
        total_llm_calls=total_llm_calls,
        validation_errors=validation_errors,
        user_instructions=user_instructions,
        created_at=created_at or datetime.now(UTC),
    )
