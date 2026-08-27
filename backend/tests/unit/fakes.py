"""Fakes tipados a los puertos del dominio. Un solo lugar, sin duplicacion."""

from __future__ import annotations

import dataclasses
from typing import Any

from kosmo.contracts.ai.ai_config import UserAiConfig, UserAiConfigRepository
from kosmo.contracts.ai.chat import (
    ChatHistoryId,
    ChatSession,
    ChatSessionSummary,
    HistorialChat,
    MensajeChat,
)
from kosmo.contracts.ai.consistency import (
    ConsistencyEvaluation,
    ConsistencyEvaluationStatus,
)
from kosmo.contracts.audit.events import AuditEvent
from kosmo.contracts.auth import AuthorizationCode, RefreshConsumeResult, User, UserAlreadyExistsError
from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.document import RichTextDocument, SpecPhase
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import (
    ChatSessionId,
    ConsistencyEvaluationId,
    FeatureId,
    ProjectId,
)
from kosmo.contracts.sdd.project import Project

_MAX_FAILURES = 10
_LOCKOUT_SECONDS = 900


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}

    async def by_id(self, project_id: ProjectId) -> Project | None:
        return self.projects.get(str(project_id))

    async def by_slug(self, owner_id: str, slug: str) -> Project | None:
        return next(
            (p for p in self.projects.values() if str(p.owner_id) == owner_id and p.slug == slug),
            None,
        )

    async def find_by_slug(self, slug: str) -> Project | None:
        return next((p for p in self.projects.values() if p.slug == slug), None)

    async def list_by_owner(self, owner_id: str) -> list[Project]:
        return [p for p in self.projects.values() if str(p.owner_id) == owner_id]

    async def save(self, project: Project) -> Project:  # type: ignore[override]
        self.projects[str(project.id)] = project
        return project

    async def delete(self, project_id: ProjectId) -> None:
        self.projects.pop(str(project_id), None)


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.discovery_docs: dict[str, RichTextDocument] = {}
        self.versions: dict[str, str] = {}
        self._version_projects: dict[str, str] = {}
        self._latest_version: dict[tuple[str, str], str] = {}
        self._version_counter = 0
        self.locked_project_ids: list[str] = []

    async def get_discovery(
        self,
        project_id: ProjectId,
        *,
        for_update: bool = False,
    ) -> RichTextDocument | None:
        if for_update:
            self.locked_project_ids.append(str(project_id))
        return self.discovery_docs.get(str(project_id))

    async def save_discovery(self, project_id: ProjectId, document: RichTextDocument) -> RichTextDocument:
        self.discovery_docs[str(project_id)] = document
        return document

    async def delete_discovery(self, project_id: ProjectId) -> None:
        self.discovery_docs.pop(str(project_id), None)

    async def delete_versions_by_project(self, project_id: ProjectId) -> None:
        for version_id in list(self._version_projects):
            if self._version_projects[version_id] == str(project_id):
                self.versions.pop(version_id, None)
                del self._version_projects[version_id]
        self._latest_version = {
            (pid, phase): markdown for (pid, phase), markdown in self._latest_version.items() if pid != str(project_id)
        }

    async def get_requirements(self, feature_id: Any) -> RichTextDocument | None:  # noqa: ARG002
        return None

    async def save_requirements(
        self,
        feature_id: Any,  # noqa: ARG002
        document: RichTextDocument,  # noqa: ARG002
    ) -> RichTextDocument:
        return document

    async def save_version(  # type: ignore[override]
        self, project_id: ProjectId, phase: object, markdown: str, change_ids: list[object]
    ) -> str:
        self._version_counter += 1
        version_id = f"ver_{self._version_counter}"
        self.versions[version_id] = markdown
        self._version_projects[version_id] = str(project_id)
        phase_value = phase.value if hasattr(phase, "value") else str(phase)
        self._latest_version[(str(project_id), phase_value)] = markdown
        return version_id

    async def get_version(self, version_id: str) -> str | None:
        return self.versions.get(version_id)

    async def get_latest_version(self, project_id: ProjectId, phase: object) -> str | None:
        phase_value = phase.value if hasattr(phase, "value") else str(phase)
        return self._latest_version.get((str(project_id), phase_value))


class InMemoryFeatureRepository:
    def __init__(self) -> None:
        self.features: dict[str, Feature] = {}
        self.locked_feature_ids: list[str] = []

    async def by_id(self, feature_id: FeatureId, *, for_update: bool = False) -> Feature | None:
        if for_update:
            self.locked_feature_ids.append(str(feature_id))
        return self.features.get(str(feature_id))

    async def list_by_project(self, project_id: ProjectId) -> list[Feature]:
        return sorted(
            (f for f in self.features.values() if str(f.project_id) == str(project_id)),
            key=lambda feature: feature.number,
        )

    async def save(self, feature: Feature) -> Feature:  # type: ignore[override]
        self.features[str(feature.id)] = feature
        return feature

    async def save_many(self, features: list[Feature]) -> list[Feature]:  # type: ignore[override]
        for f in features:
            self.features[str(f.id)] = f
        return features

    async def next_number(self, project_id: ProjectId) -> int:
        project_features = [f for f in self.features.values() if str(f.project_id) == str(project_id)]
        return max((f.number for f in project_features), default=0) + 1

    async def delete(self, feature_id: FeatureId) -> None:
        self.features.pop(str(feature_id), None)


class InMemoryRequirementRepository:
    def __init__(self) -> None:
        self._requirements: dict[str, str] = {}
        self.locked_feature_ids: list[str] = []

    async def save(self, feature_id: FeatureId, markdown: str) -> None:
        self._requirements[str(feature_id)] = markdown

    async def by_feature_id(self, feature_id: FeatureId, *, for_update: bool = False) -> str | None:
        if for_update:
            self.locked_feature_ids.append(str(feature_id))
        return self._requirements.get(str(feature_id))

    async def delete(self, feature_id: FeatureId) -> None:
        self._requirements.pop(str(feature_id), None)


class InMemoryActivityDiagramRepository:
    def __init__(self) -> None:
        self._diagrams: dict[str, DiagramaActividad] = {}
        self.locked_feature_ids: list[str] = []

    async def save(self, diagram: DiagramaActividad) -> DiagramaActividad:
        self._diagrams[str(diagram.feature_id)] = diagram
        return diagram

    async def by_feature_id(
        self,
        feature_id: FeatureId,
        *,
        for_update: bool = False,
    ) -> DiagramaActividad | None:
        if for_update:
            self.locked_feature_ids.append(str(feature_id))
        return self._diagrams.get(str(feature_id))

    async def exists(self, feature_id: FeatureId) -> bool:
        return str(feature_id) in self._diagrams

    async def delete(self, feature_id: FeatureId) -> None:
        self._diagrams.pop(str(feature_id), None)


class StubEmbedder:
    def __init__(self, model_name: str = "stub-embedder", dimensions: int = 4) -> None:
        self._model_name = model_name
        self._dims = dimensions

    @property
    def model_name(self) -> str:
        return self._model_name

    async def embed(self, text: str) -> list[float] | None:  # noqa: ARG002
        import hashlib

        h = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in h[: self._dims]]

    @staticmethod
    def text_for_embedding(output: object, validation_errors: list[str]) -> str:
        parts = [str(output)[:2000]]
        if validation_errors:
            parts.append("Errores: " + "; ".join(validation_errors[:5]))
        return "\n".join(parts)


class InMemoryAuditEventSink:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def record(self, event: AuditEvent) -> None:
        self.events.append(event)


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}

    async def by_email(self, email: str) -> User | None:
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    async def by_id(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    async def create(self, user: User) -> None:
        if any(u.email == user.email for u in self.users.values()):
            raise UserAlreadyExistsError("Email ya registrado")
        self.users[user.id] = user

    async def update_password(self, *, user_id: str, hashed_password: str) -> None:
        existing = self.users.get(user_id)
        if existing is None:
            return
        self.users[user_id] = User(
            id=existing.id,
            email=existing.email,
            hashed_password=hashed_password,
            created_at=existing.created_at,
            disabled_at=existing.disabled_at,
        )


class InMemoryAuthorizationCodeStore:
    def __init__(self) -> None:
        self.entries: dict[str, AuthorizationCode] = {}

    async def store(self, entry: AuthorizationCode) -> None:
        self.entries[entry.code] = entry

    async def consume(self, code: str) -> AuthorizationCode | None:
        return self.entries.pop(code, None)


class InMemoryLoginAttemptStore:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    async def record_failure(self, identifier: str) -> None:
        self._counts[identifier] = self._counts.get(identifier, 0) + 1

    async def clear(self, identifier: str) -> None:
        self._counts.pop(identifier, None)

    async def lockout_seconds(self, identifier: str) -> int | None:
        count = self._counts.get(identifier, 0)
        return _LOCKOUT_SECONDS if count >= _MAX_FAILURES else None


class InMemoryStore:
    def __init__(self) -> None:
        self.refresh: dict[str, tuple[str, str | None]] = {}
        self.revoked_access: set[str] = set()
        self.families: set[str] = set()

    async def register_refresh(
        self,
        *,
        jti: str,
        subject: str,
        ttl_seconds: int,
        family_id: str | None = None,
    ) -> None:
        if ttl_seconds <= 0:
            return
        self.refresh[jti] = (subject, family_id)
        if family_id is not None:
            self.families.add(family_id)

    async def consume_refresh(self, *, jti: str) -> RefreshConsumeResult | None:
        entry = self.refresh.pop(jti, None)
        if entry is None:
            return None
        return RefreshConsumeResult(subject=entry[0], family_id=entry[1])

    async def revoke_access(self, *, jti: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        self.revoked_access.add(jti)

    async def is_access_revoked(self, *, jti: str) -> bool:
        return jti in self.revoked_access

    async def revoke_refresh(self, *, jti: str) -> None:
        self.refresh.pop(jti, None)

    async def is_family_alive(self, *, family_id: str) -> bool:
        return family_id in self.families

    async def revoke_family(self, *, family_id: str) -> None:
        self.families.discard(family_id)
        for jti in list(self.refresh):
            if self.refresh[jti][1] == family_id:
                del self.refresh[jti]


class InMemoryTraceabilityRepository:
    def __init__(self) -> None:
        self.edges: list[tuple[str, str, str, str, str]] = []

    async def get_impact(self, artifact_id: str) -> dict[str, list[dict[str, str]]]:
        upstream = [
            {"type": source_type, "id": source_id, "origin": origin}
            for source_type, source_id, _target_type, target_id, origin in self.edges
            if target_id == artifact_id
        ]
        downstream = [
            {"type": target_type, "id": target_id, "origin": origin}
            for _source_type, source_id, target_type, target_id, origin in self.edges
            if source_id == artifact_id
        ]
        return {"upstream": upstream, "downstream": downstream}

    async def add_edge(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        origin: str = "llm",
    ) -> None:
        self.edges.append((source_type, source_id, target_type, target_id, origin))

    async def add_feature_requirement_edges(self, feature_id: FeatureId, requirement_ids: list[Any]) -> None:
        for req_id in requirement_ids:
            self.edges.append(("feature", str(feature_id), "requirement", str(req_id), "llm"))

    async def delete_by_entity_id(self, entity_id: str) -> None:
        self.edges = [edge for edge in self.edges if edge[1] != entity_id and edge[3] != entity_id]


class InMemoryOutbox:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict[str, Any]]] = []

    async def enqueue(self, job_type: str, payload: dict[str, Any]) -> None:
        self.jobs.append((job_type, payload))


class InMemoryConsistencyEvaluationRepository:
    def __init__(self) -> None:
        self._rows: dict[str, ConsistencyEvaluation] = {}
        self._by_key: dict[tuple[str, str, str, str], ConsistencyEvaluation] = {}

    async def save(self, evaluation: ConsistencyEvaluation) -> ConsistencyEvaluation:
        key = (
            str(evaluation.project_id),
            evaluation.source_phase.value,
            evaluation.target_phase.value,
            evaluation.target_artifact_id,
        )
        existing = self._by_key.get(key)
        stored = dataclasses.replace(evaluation, id=existing.id) if existing is not None else evaluation
        self._by_key[key] = stored
        self._rows[str(stored.id)] = stored
        return stored

    async def by_id(self, evaluation_id: ConsistencyEvaluationId) -> ConsistencyEvaluation | None:
        return self._rows.get(str(evaluation_id))

    async def list_unresolved(
        self,
        project_id: ProjectId,
        target_phase: SpecPhase,
    ) -> list[ConsistencyEvaluation]:
        unresolved = {
            ConsistencyEvaluationStatus.EVALUATING,
            ConsistencyEvaluationStatus.COMPLETED,
            ConsistencyEvaluationStatus.FAILED,
        }
        return [
            e
            for e in self._rows.values()
            if str(e.project_id) == str(project_id) and e.target_phase == target_phase and e.status in unresolved
        ]

    async def list_for_activity(
        self,
        project_id: ProjectId,
        *,
        limit: int = 50,
    ) -> list[ConsistencyEvaluation]:
        resolved = {ConsistencyEvaluationStatus.APPLIED, ConsistencyEvaluationStatus.DISCARDED}
        return [e for e in self._rows.values() if str(e.project_id) == str(project_id) and e.status in resolved][:limit]

    async def delete_by_project(self, project_id: ProjectId) -> None:
        for key in list(self._by_key):
            if key[0] == str(project_id):
                evaluation = self._by_key.pop(key)
                self._rows.pop(str(evaluation.id), None)


class InMemoryUnitOfWork:
    def __init__(
        self,
        *,
        projects: InMemoryProjectRepository | None = None,
        documents: InMemoryDocumentRepository | None = None,
        features: InMemoryFeatureRepository | None = None,
        requirements: InMemoryRequirementRepository | None = None,
        diagrams: InMemoryActivityDiagramRepository | None = None,
        chat: InMemoryChatRepository | None = None,
        traceability: InMemoryTraceabilityRepository | None = None,
        outbox: InMemoryOutbox | None = None,
    ) -> None:
        self.projects = projects or InMemoryProjectRepository()
        self.documents = documents or InMemoryDocumentRepository()
        self.features = features or InMemoryFeatureRepository()
        self.requirements = requirements or InMemoryRequirementRepository()
        self.diagrams = diagrams or InMemoryActivityDiagramRepository()
        self.chat = chat or InMemoryChatRepository()
        self.traceability = traceability or InMemoryTraceabilityRepository()
        self.outbox = outbox or InMemoryOutbox()

    async def __aenter__(self) -> InMemoryUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class InMemoryChatRepository:
    def __init__(self) -> None:
        self.messages: list[MensajeChat] = []
        self.sessions: list[ChatSession] = []
        self._message_sessions: list[tuple[MensajeChat, ChatSessionId | None]] = []

    async def save_message(
        self,
        project_id: ProjectId,  # noqa: ARG002
        phase: SpecPhase,  # noqa: ARG002
        message: MensajeChat,
        context_id: str | None = None,  # noqa: ARG002
        session_id: ChatSessionId | None = None,
    ) -> MensajeChat:
        self.messages.append(message)
        self._message_sessions.append((message, session_id))
        return message

    async def get_history(
        self,
        project_id: ProjectId,  # noqa: ARG002
        phase: SpecPhase,  # noqa: ARG002
        context_id: str | None = None,  # noqa: ARG002
        limit: int = 200,  # noqa: ARG002
        before: str | None = None,  # noqa: ARG002
        session_id: ChatSessionId | None = None,
    ) -> HistorialChat | None:
        selected = [
            msg
            for msg, sid in self._message_sessions
            if (session_id is None and sid is None) or (session_id is not None and sid == session_id)
        ]
        if not selected:
            return None
        return HistorialChat(
            id=ChatHistoryId("hist_test"),
            project_id=project_id,
            phase=phase,
            context_id=context_id,
            session_id=session_id,
            messages=tuple(selected),
        )

    async def save_history(self, history: HistorialChat) -> HistorialChat:
        self.messages = list(history.messages)
        return history

    async def create_session(self, session: ChatSession) -> ChatSession:
        self.sessions.append(session)
        return session

    async def delete_session(self, session_id: ChatSessionId) -> None:
        self.sessions = [s for s in self.sessions if s.id != session_id]
        self._message_sessions = [(msg, sid) for msg, sid in self._message_sessions if sid != session_id]

    async def delete_by_project(self, project_id: ProjectId) -> None:
        project_sessions = {s.id for s in self.sessions if str(s.project_id) == str(project_id)}
        self.sessions = [s for s in self.sessions if s.id not in project_sessions]
        self._message_sessions = [
            (msg, sid) for msg, sid in self._message_sessions if sid is None or sid not in project_sessions
        ]
        self.messages = [msg for msg, _sid in self._message_sessions]

    async def list_sessions(
        self,
        project_id: ProjectId,  # noqa: ARG002
        phase: SpecPhase,
        *,
        context_id: str | None = None,  # noqa: ARG002
    ) -> list[ChatSessionSummary]:
        summaries: list[ChatSessionSummary] = []
        for session in self.sessions:
            if session.phase != phase:
                continue
            count = sum(1 for _msg, sid in self._message_sessions if sid == session.id)
            summaries.append(
                ChatSessionSummary(
                    id=session.id,
                    phase=session.phase,
                    context_id=session.context_id,
                    created_at=session.created_at,
                    message_count=count,
                )
            )
        return summaries


class FakeConsistencyEvaluator:
    def __init__(self) -> None:
        self._results: dict[str, dict[str, list[str]]] = {}
        self._should_fail: bool = False

    def set_affected_ids(self, target_phase: str, artifact_ids: list[str]) -> None:
        self._results[target_phase] = {"artifact_ids": artifact_ids}

    def set_should_fail(self, value: bool = True) -> None:
        self._should_fail = value

    async def evaluate(
        self,
        *,
        source_phase: SpecPhase,  # noqa: ARG002
        target_phase: SpecPhase,
        project_id: ProjectId,  # noqa: ARG002
        applied_changes: list[object],  # noqa: ARG002
    ) -> Any:
        from kosmo.contracts.ai.consistency import ConsistencyEvaluationOutput

        if self._should_fail:
            raise RuntimeError("Fake evaluator failure")

        phase_key = target_phase.value if hasattr(target_phase, "value") else str(target_phase)
        result = self._results.get(phase_key, {"artifact_ids": []})
        affected = result.get("artifact_ids", [])
        from kosmo.contracts.ai.consistency import ConsistencyStatus

        status = ConsistencyStatus.ANALIZADO_CON_IMPACTO if affected else ConsistencyStatus.ANALIZADO_SIN_IMPACTO
        return ConsistencyEvaluationOutput(report_id="rpt_fake", status=status, affected_artifact_ids=affected)


class InMemoryUserAiConfigRepository(UserAiConfigRepository):
    """Implementa UserAiConfigRepository en memoria para tests unitarios."""

    def __init__(self) -> None:
        self.configs: dict[str, UserAiConfig] = {}

    async def by_user_id(self, user_id: str) -> UserAiConfig | None:
        return self.configs.get(user_id)

    async def save(self, config: UserAiConfig) -> UserAiConfig:
        self.configs[config.user_id] = config
        return config

    async def delete(self, user_id: str) -> None:
        self.configs.pop(user_id, None)


class InMemoryUserIntegrationRepository:
    """Implementa UserIntegrationRepository en memoria para tests unitarios."""

    def __init__(self) -> None:
        from kosmo.contracts.integrations.user_integration import UserIntegration

        self.integrations: dict[tuple[str, str], UserIntegration] = {}

    async def get_by_user_and_provider(
        self,
        user_id: Any,
        provider: Any,
    ) -> Any:
        from kosmo.contracts.integrations.user_integration import IntegrationProvider

        provider_str = provider.value if isinstance(provider, IntegrationProvider) else str(provider)
        return self.integrations.get((str(user_id), provider_str))

    async def save(self, integration: Any) -> Any:
        from kosmo.contracts.integrations.user_integration import IntegrationProvider

        provider_str = (
            integration.provider.value
            if isinstance(integration.provider, IntegrationProvider)
            else str(integration.provider)
        )
        self.integrations[(str(integration.user_id), provider_str)] = integration
        return integration

    async def delete(self, user_id: Any, provider: Any) -> bool:
        from kosmo.contracts.integrations.user_integration import IntegrationProvider

        provider_str = provider.value if isinstance(provider, IntegrationProvider) else str(provider)
        existed = (str(user_id), provider_str) in self.integrations
        self.integrations.pop((str(user_id), provider_str), None)
        return existed

    async def list_by_user(self, user_id: Any) -> list[Any]:
        user_str = str(user_id)
        return [i for (u, _), i in self.integrations.items() if u == user_str]


class InMemoryUserGitHubIntegrationRepository:
    """Implementa UserGitHubIntegrationRepository en memoria para tests unitarios."""

    def __init__(self) -> None:
        from kosmo.contracts.integrations.github import UserGitHubIntegration

        self.integrations: dict[str, UserGitHubIntegration] = {}

    async def get_by_user_id(self, user_id: Any) -> Any:
        return self.integrations.get(str(user_id))

    async def save(self, integration: Any) -> None:
        self.integrations[str(integration.user_id)] = integration

    async def delete_by_user_id(self, user_id: Any) -> bool:
        existed = str(user_id) in self.integrations
        self.integrations.pop(str(user_id), None)
        return existed
