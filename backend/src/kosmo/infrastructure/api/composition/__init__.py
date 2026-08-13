from __future__ import annotations

from dataclasses import dataclass

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
    "AppContainer",
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
class AppContainer:
    """Contenedor tipado de dependencias expuesto via ``app.state.container``."""

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

    async def close(self) -> None:
        if self.redis is not None:
            await self.redis.aclose()
        await self.db_engine.dispose()


def build_app_components(settings: Settings) -> AppContainer:
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

    return AppContainer(
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
