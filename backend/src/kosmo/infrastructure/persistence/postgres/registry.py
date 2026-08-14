from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.infrastructure.persistence.postgres.repositories import (
    SqlAlchemyAuditEventSink,
    SqlAlchemyProjectRepository,
    SqlAlchemyUserRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.activity_diagram_repo import (
    SqlAlchemyActivityDiagramRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.chat_repo import SqlAlchemyChatRepository
from kosmo.infrastructure.persistence.postgres.repositories.consistency_repo import (
    SqlAlchemyConsistencyEvaluationRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.document_repo import (
    SqlAlchemyDocumentRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.feature_repo import (
    SqlAlchemyFeatureRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.requirement_repo import (
    SqlAlchemyRequirementRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.traceability_repo import (
    SqlAlchemyTraceabilityRepository,
)


@dataclass(frozen=True, slots=True)
class RepositoryRegistry:
    """Fuente unica de repositorios SQL: cada uno se instancia exactamente una vez."""

    projects: SqlAlchemyProjectRepository
    documents: SqlAlchemyDocumentRepository
    features: SqlAlchemyFeatureRepository
    requirements: SqlAlchemyRequirementRepository
    diagrams: SqlAlchemyActivityDiagramRepository
    chat: SqlAlchemyChatRepository
    traceability: SqlAlchemyTraceabilityRepository
    users: SqlAlchemyUserRepository
    audit_sink: SqlAlchemyAuditEventSink
    consistency_evaluations: SqlAlchemyConsistencyEvaluationRepository

    @classmethod
    def build(cls, session_factory: async_sessionmaker[AsyncSession]) -> RepositoryRegistry:
        return cls(
            projects=SqlAlchemyProjectRepository(session_factory),
            documents=SqlAlchemyDocumentRepository(session_factory),
            features=SqlAlchemyFeatureRepository(session_factory),
            requirements=SqlAlchemyRequirementRepository(session_factory),
            diagrams=SqlAlchemyActivityDiagramRepository(session_factory),
            chat=SqlAlchemyChatRepository(session_factory),
            traceability=SqlAlchemyTraceabilityRepository(session_factory),
            users=SqlAlchemyUserRepository(session_factory),
            audit_sink=SqlAlchemyAuditEventSink(session_factory),
            consistency_evaluations=SqlAlchemyConsistencyEvaluationRepository(session_factory),
        )
