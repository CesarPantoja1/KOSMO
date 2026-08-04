"""Fakes tipados a los puertos del dominio. Un solo lugar, sin duplicacion."""

from __future__ import annotations

from typing import Any

from kosmo.contracts.audit.events import AuditEvent
from kosmo.contracts.auth import AuthorizationCode, RefreshConsumeResult, User, UserAlreadyExistsError
from kosmo.contracts.chat import (
    ChatHistoryId,
    EstadoPlanCambio,
    HistorialChat,
    MensajeChat,
    PlanCambio,
)
from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.document import RichTextDocument, SpecPhase
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, PlanChangeId, ProjectId
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


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.discovery_docs: dict[str, RichTextDocument] = {}
        self.versions: dict[str, str] = {}
        self._version_counter = 0

    async def get_discovery(self, project_id: ProjectId) -> RichTextDocument | None:
        return self.discovery_docs.get(str(project_id))

    async def save_discovery(self, project_id: ProjectId, document: RichTextDocument) -> RichTextDocument:
        self.discovery_docs[str(project_id)] = document
        return document

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
        return version_id

    async def get_version(self, version_id: str) -> str | None:
        return self.versions.get(version_id)


class InMemoryFeatureRepository:
    def __init__(self) -> None:
        self.features: dict[str, Feature] = {}

    async def by_id(self, feature_id: FeatureId) -> Feature | None:
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
        self._items: dict[str, list[dict]] = {}

    async def save(self, feature_id: FeatureId, markdown: str) -> None:
        self._requirements[str(feature_id)] = markdown

    async def by_feature_id(self, feature_id: FeatureId) -> str | None:
        return self._requirements.get(str(feature_id))

    async def save_items(self, feature_id: FeatureId, items: list[object]) -> None:  # type: ignore[override]
        self._items[str(feature_id)] = [
            dict(item) if isinstance(item, dict) else item.__dict__  # type: ignore[reportUnknownVariableType]
            for item in items
        ]  # type: ignore[reportUnknownVariableType]

    async def list_items(self, feature_id: FeatureId) -> list[object]:  # type: ignore[override]
        return self._items.get(str(feature_id), [])


class InMemoryActivityDiagramRepository:
    def __init__(self) -> None:
        self._diagrams: dict[str, DiagramaActividad] = {}

    async def save(self, diagram: DiagramaActividad) -> DiagramaActividad:
        self._diagrams[str(diagram.feature_id)] = diagram
        return diagram

    async def by_feature_id(self, feature_id: FeatureId) -> DiagramaActividad | None:
        return self._diagrams.get(str(feature_id))

    async def exists(self, feature_id: FeatureId) -> bool:
        return str(feature_id) in self._diagrams


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


class InMemoryChatRepository:
    def __init__(self) -> None:
        self.messages: list[MensajeChat] = []
        self.plans: list[PlanCambio] = []

    async def save_message(
        self,
        project_id: ProjectId,  # noqa: ARG002
        phase: SpecPhase,  # noqa: ARG002
        message: MensajeChat,
        context_id: str | None = None,  # noqa: ARG002
    ) -> MensajeChat:
        self.messages.append(message)
        return message

    async def get_history(
        self,
        project_id: ProjectId,  # noqa: ARG002
        phase: SpecPhase,  # noqa: ARG002
        context_id: str | None = None,  # noqa: ARG002
    ) -> HistorialChat | None:
        return HistorialChat(
            id=ChatHistoryId("hist_test"),
            project_id=project_id,
            phase=phase,
            context_id=context_id,
            messages=tuple(self.messages),
        )

    async def save_history(self, history: HistorialChat) -> HistorialChat:
        self.messages = list(history.messages)
        return history

    async def add_plan_change(
        self,
        project_id: ProjectId,  # noqa: ARG002
        phase: SpecPhase,  # noqa: ARG002
        change: PlanCambio,
    ) -> PlanCambio:
        self.plans.append(change)
        return change

    async def list_plan_changes(
        self,
        project_id: ProjectId,  # noqa: ARG002
        phase: SpecPhase | None = None,  # noqa: ARG002
    ) -> list[PlanCambio]:
        return self.plans

    async def update_plan_change_status(
        self,
        project_id: ProjectId,  # noqa: ARG002
        change_id: PlanChangeId,
        status: EstadoPlanCambio,
        user_version: str | None = None,
    ) -> PlanCambio | None:
        for idx, item in enumerate(self.plans):
            if item.id == change_id:
                updated = PlanCambio(
                    id=item.id,
                    section=item.section,
                    description=item.description,
                    diff=item.diff,
                    status=status,
                    origin=item.origin,
                    rationale=item.rationale,
                    user_version=user_version or item.user_version,
                    context_id=item.context_id,
                )
                self.plans[idx] = updated
                return updated
        return None

    async def remove_plan_change(
        self,
        project_id: ProjectId,  # noqa: ARG002
        change_id: PlanChangeId,
    ) -> bool:
        initial_len = len(self.plans)
        self.plans = [p for p in self.plans if p.id != change_id]
        return len(self.plans) < initial_len

    async def clear_plan(
        self,
        project_id: ProjectId,  # noqa: ARG002
        phase: SpecPhase | None = None,  # noqa: ARG002
    ) -> None:
        self.plans.clear()


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
        applied_changes: list[PlanCambio],  # noqa: ARG002
    ) -> Any:
        from kosmo.contracts.consistency import ConsistencyEvaluationOutput

        if self._should_fail:
            raise RuntimeError("Fake evaluator failure")

        phase_key = target_phase.value if hasattr(target_phase, "value") else str(target_phase)
        result = self._results.get(phase_key, {"artifact_ids": []})
        affected = result.get("artifact_ids", [])
        return ConsistencyEvaluationOutput(report_id="rpt_fake", affected_artifact_ids=affected)
