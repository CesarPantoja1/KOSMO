from __future__ import annotations

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.requests import Request

from kosmo.application.chat.apply_plan_changes import ApplyPlanChangesUseCase
from kosmo.application.chat.process_chat_message import ProcessChatMessageUseCase
from kosmo.application.consistency.apply_consistency_impacts import ApplyConsistencyImpactsUseCase
from kosmo.config import Settings
from kosmo.infrastructure.api.composition import AppContainer, build_app_components
from kosmo.infrastructure.api.dependencies.container import get_container
from kosmo.infrastructure.persistence.postgres.registry import RepositoryRegistry


def _make_settings() -> Settings:
    return Settings(
        env="development",
        database_url="postgresql+asyncpg://user:pass@localhost:5432/kosmo",
        llm_provider="noop",
        llm_model="noop",
        embedding_provider="none",
        auth_disabled=True,
    )


@pytest.mark.unit
def test_repository_registry_builds_distinct_repositories() -> None:
    # Arrange
    factory = async_sessionmaker()

    # Act
    repos = RepositoryRegistry.build(factory)

    # Assert
    instances = [
        repos.projects,
        repos.documents,
        repos.features,
        repos.requirements,
        repos.diagrams,
        repos.chat,
        repos.traceability,
        repos.users,
        repos.audit_sink,
    ]
    assert len({id(repo) for repo in instances}) == len(instances)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_app_components_reuses_registry_instances() -> None:
    # Arrange
    settings = _make_settings()

    # Act
    components = build_app_components(settings)

    try:
        # Assert: cada builder usa la instancia unica del registry
        assert components.discovery.document_repo is components.repos.documents
        assert components.features.feature_repo is components.repos.features
        assert components.requirements.requirement_repo is components.repos.requirements
        assert components.modelo.diagram_repo is components.repos.diagrams
        assert components.pipeline.chat_repo is components.repos.chat
        assert components.pipeline.traceability_repo is components.repos.traceability

        # Assert: auth deshabilitado no crea componentes de autenticacion
        assert components.auth is None
        assert components.redis is None
    finally:
        await components.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_app_container_exposes_typed_components() -> None:
    # Arrange
    settings = _make_settings()

    # Act
    components = build_app_components(settings)

    try:
        # Assert: los campos del contenedor tienen tipos concretos (no Any)
        assert isinstance(components, AppContainer)
        assert isinstance(components.pipeline.process_chat_message, ProcessChatMessageUseCase)
        assert isinstance(components.discovery.apply_plan_changes, ApplyPlanChangesUseCase)
        assert isinstance(components.consistency.apply_consistency_impacts, ApplyConsistencyImpactsUseCase)
        assert components.projects.create_project is not None
        assert components.pipeline.outbox is not None
        assert components.db_engine is not None
    finally:
        await components.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_container_returns_container_from_app_state() -> None:
    # Arrange
    settings = _make_settings()
    components = build_app_components(settings)
    app = FastAPI()
    app.state.container = components
    request = Request(scope={"type": "http", "method": "GET", "path": "/", "app": app})

    # Act
    container = get_container(request)

    # Assert
    assert container is components

    await components.close()
