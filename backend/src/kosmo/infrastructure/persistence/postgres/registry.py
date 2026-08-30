from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.infrastructure.persistence.postgres.repositories import (
    SqlAlchemyActivityDiagramRepository,
    SqlAlchemyAuditEventSink,
    SqlAlchemyChatRepository,
    SqlAlchemyCodeSyncLogRepository,
    SqlAlchemyConsistencyEvaluationRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyFeatureImplementationRepository,
    SqlAlchemyFeatureRepository,
    SqlAlchemyProjectGitHubIntegrationRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyRequirementRepository,
    SqlAlchemyTraceabilityRepository,
    SqlAlchemyUserAiConfigRepository,
    SqlAlchemyUserGitHubIntegrationRepository,
    SqlAlchemyUserIntegrationRepository,
    SqlAlchemyUserRepository,
    SqlAlchemyWorkspaceRepository,
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
    workspaces: SqlAlchemyWorkspaceRepository
    implementations: SqlAlchemyFeatureImplementationRepository
    user_ai_configs: SqlAlchemyUserAiConfigRepository
    project_integrations: SqlAlchemyProjectGitHubIntegrationRepository
    sync_logs: SqlAlchemyCodeSyncLogRepository
    user_integrations: SqlAlchemyUserIntegrationRepository
    user_github_integrations: SqlAlchemyUserGitHubIntegrationRepository

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
            workspaces=SqlAlchemyWorkspaceRepository(session_factory),
            implementations=SqlAlchemyFeatureImplementationRepository(session_factory),
            user_ai_configs=SqlAlchemyUserAiConfigRepository(session_factory),
            project_integrations=SqlAlchemyProjectGitHubIntegrationRepository(session_factory),
            sync_logs=SqlAlchemyCodeSyncLogRepository(session_factory),
            user_integrations=SqlAlchemyUserIntegrationRepository(session_factory),
            user_github_integrations=SqlAlchemyUserGitHubIntegrationRepository(session_factory),
        )
