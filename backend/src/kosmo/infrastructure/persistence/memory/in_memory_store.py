from __future__ import annotations

from datetime import UTC, datetime

from kosmo.contracts.agent_memory import (
    AgentMemoryPort,
    AgentSession,
    AgentSessionSummary,
    KnowledgePattern,
    ProjectMemoryContext,
)
from kosmo.contracts.chat import (
    ChatRepository,
    ChatSession,
    ChatSessionSummary,
    HistorialChat,
    MensajeChat,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import AgentMemoryId, ChatHistoryId, ChatSessionId, ProjectId


class InMemoryAgentSessionStore(AgentMemoryPort):
    def __init__(self) -> None:
        self._store: dict[str, AgentSession] = {}

    async def save_session(self, session: AgentSession) -> None:
        self._store[session.session_id] = session

    async def update_reflection(self, session_id: AgentMemoryId, reflection: str) -> None:
        session = self._store.get(session_id)
        if session is not None:
            self._store[session_id] = AgentSession(
                session_id=session.session_id,
                project_id=session.project_id,
                session_type=session.session_type,
                phase=session.phase,
                skill_name=session.skill_name,
                conversation=session.conversation,
                reasoning_log=list(session.reasoning_log) + [f"reflexion: {reflection}"],
                tool_results=session.tool_results,
                current_iteration=session.current_iteration,
                max_iterations=session.max_iterations,
                is_completed=session.is_completed,
                output_json=session.output_json,
                validation_is_valid=session.validation_is_valid,
                validation_errors=session.validation_errors,
                validation_error_messages=session.validation_error_messages,
                total_llm_calls=session.total_llm_calls,
                user_instructions=session.user_instructions,
                embedding=session.embedding,
                embedding_model=session.embedding_model,
                reflection=reflection,
                created_at=session.created_at,
                updated_at=datetime.now(UTC),
            )

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
        failed_sessions = [
            s
            for s in self._store.values()
            if s.project_id == project_id and not s.is_completed and s.validation_error_messages
        ]
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

        common_errors = [f"{msg} (x{count})" for msg, count in sorted(error_counter.items(), key=lambda x: -x[1])[:5]]

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
        model: str | None = None,
    ) -> list[AgentSessionSummary]:
        scored: list[tuple[float, AgentSessionSummary]] = []
        for session in self._store.values():
            if exclude_project_id is not None and session.project_id == exclude_project_id:
                continue
            if session.embedding is None:
                continue
            if model is not None and session.embedding_model != model:
                continue
            sim = _cosine_similarity(embedding, session.embedding)
            scored.append((sim, _to_summary(session)))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]]

    async def list_recent_sessions_global(
        self,
        *,
        limit: int = 50,
    ) -> list[AgentSessionSummary]:
        sessions = sorted(self._store.values(), key=lambda s: s.created_at, reverse=True)
        return [_to_summary(s) for s in sessions[:limit]]

    async def count_completed_by_phase(
        self,
        *,
        since_session_id: AgentMemoryId | None = None,
        project_id: ProjectId | None = None,
    ) -> dict[str, int]:
        cutoff: datetime | None = None
        if since_session_id is not None:
            ref = self._store.get(since_session_id)
            if ref is not None:
                cutoff = ref.created_at
        counts: dict[str, int] = {}
        for s in self._store.values():
            if not s.is_completed:
                continue
            if cutoff is not None and s.created_at <= cutoff:
                continue
            if project_id is not None and s.project_id != project_id:
                continue
            key = s.phase.value
            counts[key] = counts.get(key, 0) + 1
        return counts


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
        reflection=session.reflection,
    )


class InMemoryKnowledgePatternStore:
    def __init__(self) -> None:
        self._patterns: dict[str, list[KnowledgePattern]] = {}

    async def replace_patterns(
        self,
        phase: SpecPhase,
        patterns: list[KnowledgePattern],
    ) -> None:
        self._patterns[phase.value] = patterns

    async def list_patterns(
        self,
        phase: SpecPhase | None = None,
        *,
        limit: int = 10,
    ) -> list[KnowledgePattern]:
        results: list[KnowledgePattern] = []
        for phase_key, pats in self._patterns.items():
            if phase is not None and phase_key != phase.value:
                continue
            results.extend(pats)
        results.sort(key=lambda p: p.support_count, reverse=True)
        return results[:limit]


class InMemoryChatRepository(ChatRepository):
    def __init__(self) -> None:
        self._messages: dict[str, list[MensajeChat]] = {}
        self._sessions: list[ChatSession] = []

    @staticmethod
    def _composite_key(
        project_id: ProjectId,
        phase: SpecPhase,
        context_id: str | None,
        session_id: ChatSessionId | None = None,
    ) -> str:
        if session_id is not None:
            return f"{project_id}_{phase.value}_s_{session_id}"
        return f"{project_id}_{phase.value}_{context_id or ''}"

    async def save_message(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        message: MensajeChat,
        context_id: str | None = None,
        session_id: ChatSessionId | None = None,
    ) -> MensajeChat:
        key = self._composite_key(project_id, phase, context_id, session_id)
        if key not in self._messages:
            self._messages[key] = []
        self._messages[key].append(message)
        return message

    async def get_history(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        context_id: str | None = None,
        limit: int = 200,
        before: str | None = None,  # noqa: ARG002  # ponytail: implementar cuando se necesite cursor in-memory
        session_id: ChatSessionId | None = None,
    ) -> HistorialChat | None:
        key = self._composite_key(project_id, phase, context_id, session_id)
        messages = self._messages.get(key)
        if not messages:
            return None

        recent = messages[-limit:]
        return HistorialChat(
            id=ChatHistoryId(key),
            project_id=project_id,
            phase=phase,
            context_id=context_id,
            session_id=session_id,
            messages=tuple(recent),
        )

    async def save_history(self, history: HistorialChat) -> HistorialChat:
        return history

    async def create_session(self, session: ChatSession) -> ChatSession:
        self._sessions.append(session)
        return session

    async def list_sessions(
        self,
        project_id: ProjectId,  # noqa: ARG002
        phase: SpecPhase,
        *,
        context_id: str | None = None,  # noqa: ARG002
    ) -> list[ChatSessionSummary]:
        return [
            ChatSessionSummary(
                id=s.id,
                phase=s.phase,
                context_id=s.context_id,
                created_at=s.created_at,
            )
            for s in self._sessions
            if s.phase == phase
        ]
