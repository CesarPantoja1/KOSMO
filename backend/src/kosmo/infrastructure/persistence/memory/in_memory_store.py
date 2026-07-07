from __future__ import annotations

from kosmo.contracts.agent_memory import (
    AgentMemoryPort,
    AgentSession,
    AgentSessionSummary,
    ProjectMemoryContext,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import AgentMemoryId, ProjectId


class InMemoryAgentSessionStore(AgentMemoryPort):
    def __init__(self) -> None:
        self._store: dict[str, AgentSession] = {}

    async def save_session(self, session: AgentSession) -> None:
        self._store[session.session_id] = session

    async def load_session(self, session_id: AgentMemoryId) -> AgentSession | None:
        return self._store.get(session_id)

    async def list_sessions(
        self,
        project_id: ProjectId,
        *,
        phase: SpecPhase | None = None,
    ) -> list[AgentSessionSummary]:
        results: list[AgentSessionSummary] = []
        for session in self._store.values():
            if session.project_id != project_id:
                continue
            if phase is not None and session.phase != phase:
                continue
            results.append(_to_summary(session))
        results.sort(key=lambda s: s.created_at, reverse=True)
        return results

    async def get_latest_session(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
    ) -> AgentSession | None:
        latest: AgentSession | None = None
        for session in self._store.values():
            if session.project_id != project_id:
                continue
            if session.phase != phase:
                continue
            if latest is None or session.created_at > latest.created_at:
                latest = session
        return latest

    async def get_project_context(self, project_id: ProjectId) -> ProjectMemoryContext:
        summaries = await self.list_sessions(project_id)
        latest: dict[str, AgentSessionSummary] = {}
        for s in summaries:
            key = f"{s.session_type}:{s.phase.value}"
            if key not in latest or s.created_at > latest[key].created_at:
                latest[key] = s
        return ProjectMemoryContext(
            project_id=project_id,
            latest_sessions=latest,
            total_sessions=len(summaries),
        )


def _to_summary(session: AgentSession) -> AgentSessionSummary:
    return AgentSessionSummary(
        session_id=session.session_id,
        project_id=session.project_id,
        session_type=session.session_type,
        phase=session.phase,
        skill_name=session.skill_name,
        is_completed=session.is_completed,
        total_llm_calls=session.total_llm_calls,
        validation_errors=session.validation_errors,
        user_instructions=session.user_instructions,
        created_at=session.created_at,
    )
