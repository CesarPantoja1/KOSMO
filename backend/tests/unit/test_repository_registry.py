from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from kosmo.infrastructure.persistence.postgres.registry import RepositoryRegistry
from kosmo.infrastructure.persistence.postgres.repositories.feature_implementation_repo import (
    SqlAlchemyFeatureImplementationRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.project_integration_repo import (
    SqlAlchemyProjectDeploymentRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.user_ai_config_repo import (
    SqlAlchemyUserAiConfigRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.user_integration_repo import (
    SqlAlchemyUserDeploymentIntegrationRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.workspace_repo import (
    SqlAlchemyWorkspaceRepository,
)


@pytest.mark.unit
def test_registry_build_incluye_repos_de_codegen() -> None:
    # Arrange
    session_factory = MagicMock(spec=async_sessionmaker)

    # Act
    repos = RepositoryRegistry.build(session_factory)

    # Assert
    assert isinstance(repos.workspaces, SqlAlchemyWorkspaceRepository)
    assert isinstance(repos.implementations, SqlAlchemyFeatureImplementationRepository)
    assert isinstance(repos.user_ai_configs, SqlAlchemyUserAiConfigRepository)
    assert isinstance(repos.project_deployments, SqlAlchemyProjectDeploymentRepository)
    assert isinstance(repos.user_deployment_integrations, SqlAlchemyUserDeploymentIntegrationRepository)
