from __future__ import annotations

from datetime import UTC, datetime

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

        reflections: list[str] = []
        error_counter: dict[str, int] = {}
        failed_sessions = [s for s in self._store.values() if s.project_id == project_id
            and not s.is_completed and s.validation_error_messages]
        failed_sessions.sort(key=lambda s: s.created_at, reverse=True)
        for s in failed_sessions[:20]:
            for msg in s.validation_error_messages:
                error_counter[msg] = error_counter.get(msg, 0) + 1

        for session in self._store.values():
            if session.project_id != project_id:
                continue
            if session.reflection and session.reflection.strip():
                reflections.append(session.reflection)
        reflections.sort(
            key=lambda _r: next(
                (s.created_at for s in self._store.values() if s.reflection == _r),
                datetime.min.replace(tzinfo=UTC),
            ),
            reverse=True,
        )
        reflections = reflections[:5]

        common_errors = [f"{msg} (x{count})" for msg, count in
            sorted(error_counter.items(), key=lambda x: -x[1])[:5]]

        return ProjectMemoryContext(
            project_id=project_id,
            latest_sessions=latest,
            total_sessions=len(summaries),
            common_validation_errors=common_errors,
            recent_reflections=reflections,
        )

    async def get_similar_sessions(
        self,
        embedding: list[float],
        *,
        limit: int = 5,
        exclude_project_id: ProjectId | None = None,
    ) -> list[AgentSessionSummary]:
        scored: list[tuple[float, AgentSessionSummary]] = []
        for session in self._store.values():
            if exclude_project_id is not None and session.project_id == exclude_project_id:
                continue
            if session.embedding is None:
                continue
            sim = _cosine_similarity(embedding, session.embedding)
            scored.append((sim, _to_summary(session)))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


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
