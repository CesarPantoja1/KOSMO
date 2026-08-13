from __future__ import annotations

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from kosmo.config import Settings
from kosmo.infrastructure.api.composition import build_app_components
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
async def test_app_components_binds_expected_state_attributes() -> None:
    # Arrange
    settings = _make_settings()
    components = build_app_components(settings)
    app = FastAPI()

    # Act
    components.bind_to_state(app)

    try:
        # Assert: los nombres que consumen los routers apuntan a los componentes
        state = app.state
        assert state.db_engine is components.db_engine
        assert state.redis is None
        assert state.create_project is components.projects.create_project
        assert state.get_project is components.projects.get_project
        assert state.list_projects is components.projects.list_projects
        assert state.validate_phase_context is components.pipeline.validate_phase_context
        assert state.process_chat_message is components.pipeline.process_chat_message
        assert state.context_builder is components.pipeline.context_builder
        assert state.agent is components.pipeline.agent
        assert state.chat_repo is components.pipeline.chat_repo
        assert state.traceability_repo is components.pipeline.traceability_repo
        assert state.generate_discovery is components.discovery.generate_discovery
        assert state.get_discovery is components.discovery.get_discovery
        assert state.save_discovery is components.discovery.save_discovery
        assert state.refine_discovery is components.discovery.refine_discovery
        assert state.get_discovery_chat_history is components.discovery.get_discovery_chat_history
        assert state.manage_plan_changes is components.discovery.manage_plan_changes
        assert state.apply_plan_changes is components.discovery.apply_plan_changes
        assert state.document_repo is components.discovery.document_repo
        assert state.propagate_discovery_changes is components.discovery.propagate_changes
        assert state.consistency_evaluator is components.discovery.consistency_evaluator
        assert state.evaluate_project_consistency is components.consistency.evaluate_project_consistency
        assert state.cascade_consistency is components.consistency.cascade_consistency
        assert state.apply_consistency_impacts is components.consistency.apply_consistency_impacts
        assert state.generate_features is components.features.generate_features
        assert state.suggest_features is components.features.suggest_features
        assert state.save_selected_features is components.features.save_selected_features
        assert state.create_characteristic is components.features.create_characteristic
        assert state.feature_repo is components.features.feature_repo
        assert state.get_feature_chat_history is components.features.get_feature_chat_history
        assert state.list_features is components.features.list_features
        assert state.edit_feature is components.features.edit_feature
        assert state.check_feature_consistency is components.features.check_feature_consistency
        assert state.propagate_feature_changes is components.consistency.propagate_feature_changes
        assert state.delete_feature is components.consistency.delete_feature
        assert state.generate_ears is components.requirements.generate_ears
        assert state.get_requirements is components.requirements.get_requirements
        assert state.save_requirements is components.requirements.save_requirements
        assert state.refine_requirements is components.requirements.refine_requirements
        assert state.get_requirement_chat_history is components.requirements.get_requirement_chat_history
        assert state.requirement_repo is components.requirements.requirement_repo
        assert state.regenerate_requirements is components.requirements.regenerate_requirements
        assert state.propagate_requirement_changes is components.consistency.propagate_requirement_changes
        assert state.generate_diagram is components.modelo.generate_diagram
        assert state.get_diagram is components.modelo.get_diagram
        assert state.diagram_repo is components.modelo.diagram_repo
        assert state.consolidate_patterns is components.pipeline.consolidate_patterns
        assert state.outbox is components.pipeline.outbox
    finally:
        await components.close()
