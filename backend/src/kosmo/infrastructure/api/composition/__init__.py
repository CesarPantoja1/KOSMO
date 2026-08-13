from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from kosmo.config import Settings
from kosmo.infrastructure.api.composition.auth import AuthComponents, build_auth_components
from kosmo.infrastructure.api.composition.pipeline import PipelineComponents, build_pipeline_components
from kosmo.infrastructure.api.composition.sdd import (
    ConsistencyComponents,
    DiscoveryComponents,
    FeaturesComponents,
    ModeloComponents,
    ProjectComponents,
    RequirementsComponents,
    build_consistency_components,
    build_discovery_components,
    build_features_components,
    build_modelo_components,
    build_project_components,
    build_requirements_components,
)
from kosmo.infrastructure.persistence.postgres.registry import RepositoryRegistry
from kosmo.infrastructure.persistence.postgres.uow import SqlAlchemyUnitOfWork

__all__ = [
    "AppComponents",
    "AuthComponents",
    "ConsistencyComponents",
    "DiscoveryComponents",
    "FeaturesComponents",
    "ModeloComponents",
    "PipelineComponents",
    "ProjectComponents",
    "RequirementsComponents",
    "build_app_components",
    "build_auth_components",
    "build_consistency_components",
    "build_discovery_components",
    "build_features_components",
    "build_modelo_components",
    "build_pipeline_components",
    "build_project_components",
    "build_requirements_components",
]


@dataclass(frozen=True, slots=True)
class AppComponents:
    auth: AuthComponents | None
    projects: ProjectComponents
    pipeline: PipelineComponents
    discovery: DiscoveryComponents
    features: FeaturesComponents
    requirements: RequirementsComponents
    modelo: ModeloComponents
    consistency: ConsistencyComponents
    repos: RepositoryRegistry
    uow: SqlAlchemyUnitOfWork
    db_engine: AsyncEngine
    redis: Redis | None

    def bind_to_state(self, app: FastAPI) -> None:
        state = cast(Any, app.state)
        state.db_engine = self.db_engine
        state.redis = self.redis

        auth = self.auth
        if auth is not None:
            state.register_user = auth.register_user
            state.login_attempt_store = auth.login_attempt_store
            state.authorize_with_pkce = auth.authorize_with_pkce
            state.exchange_authorization_code = auth.exchange_authorization_code
            state.issue_token_pair = auth.issue_token_pair
            state.verify_access_token = auth.verify_access_token
            state.refresh_token_pair = auth.refresh_token_pair
            state.revoke_session = auth.revoke_session
            state.password_hasher = auth.password_hasher
            state.secret_cipher = auth.secret_cipher
            state.user_repository = auth.user_repository

        projects = self.projects
        state.create_project = projects.create_project
        state.get_project = projects.get_project
        state.list_projects = projects.list_projects

        pipeline = self.pipeline
        state.validate_phase_context = pipeline.validate_phase_context
        state.process_chat_message = pipeline.process_chat_message
        state.context_builder = pipeline.context_builder
        state.agent = pipeline.agent
        state.chat_repo = pipeline.chat_repo
        state.traceability_repo = pipeline.traceability_repo
        state.consolidate_patterns = pipeline.consolidate_patterns
        state.outbox = pipeline.outbox

        discovery = self.discovery
        state.generate_discovery = discovery.generate_discovery
        state.get_discovery = discovery.get_discovery
        state.save_discovery = discovery.save_discovery
        state.refine_discovery = discovery.refine_discovery
        state.get_discovery_chat_history = discovery.get_discovery_chat_history
        state.manage_plan_changes = discovery.manage_plan_changes
        state.apply_plan_changes = discovery.apply_plan_changes
        state.document_repo = discovery.document_repo
        state.propagate_discovery_changes = discovery.propagate_changes
        state.consistency_evaluator = discovery.consistency_evaluator

        consistency = self.consistency
        state.evaluate_project_consistency = consistency.evaluate_project_consistency
        state.cascade_consistency = consistency.cascade_consistency
        state.apply_consistency_impacts = consistency.apply_consistency_impacts
        state.propagate_feature_changes = consistency.propagate_feature_changes
        state.propagate_requirement_changes = consistency.propagate_requirement_changes
        state.delete_feature = consistency.delete_feature

        features = self.features
        state.generate_features = features.generate_features
        state.suggest_features = features.suggest_features
        state.save_selected_features = features.save_selected_features
        state.create_characteristic = features.create_characteristic
        state.feature_repo = features.feature_repo
        state.get_feature_chat_history = features.get_feature_chat_history
        state.list_features = features.list_features
        state.edit_feature = features.edit_feature
        state.check_feature_consistency = features.check_feature_consistency

        requirements = self.requirements
        state.generate_ears = requirements.generate_ears
        state.get_requirements = requirements.get_requirements
        state.save_requirements = requirements.save_requirements
        state.refine_requirements = requirements.refine_requirements
        state.get_requirement_chat_history = requirements.get_requirement_chat_history
        state.requirement_repo = requirements.requirement_repo
        state.regenerate_requirements = requirements.regenerate_requirements

        modelo = self.modelo
        state.generate_diagram = modelo.generate_diagram
        state.get_diagram = modelo.get_diagram
        state.diagram_repo = modelo.diagram_repo

    async def close(self) -> None:
        if self.redis is not None:
            await self.redis.aclose()
        await self.db_engine.dispose()


def build_app_components(settings: Settings) -> AppComponents:
    db_engine = create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        connect_args={"statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    repos = RepositoryRegistry.build(session_factory)

    auth: AuthComponents | None = None
    redis: Redis | None = None
    if not settings.auth_disabled:
        auth = build_auth_components(settings, repos)
        redis = auth.redis

    pipeline = build_pipeline_components(settings, session_factory, repos)
    uow = SqlAlchemyUnitOfWork(session_factory)

    discovery = build_discovery_components(repos, pipeline, uow)
    features = build_features_components(repos, pipeline, discovery.consistency_evaluator)
    requirements = build_requirements_components(repos, pipeline, uow)
    modelo = build_modelo_components(repos, pipeline)
    projects = build_project_components(repos)
    consistency = build_consistency_components(repos, pipeline, discovery.consistency_evaluator, uow)

    return AppComponents(
        auth=auth,
        projects=projects,
        pipeline=pipeline,
        discovery=discovery,
        features=features,
        requirements=requirements,
        modelo=modelo,
        consistency=consistency,
        repos=repos,
        uow=uow,
        db_engine=db_engine,
        redis=redis,
    )
