from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kosmo.contracts.integrations.deployment import (
    DeploymentAccountNotLinkedError,
    DeploymentApiError,
    DeploymentAuthenticationError,
    DeploymentConfigurationError,
    DeploymentOAuthToken,
    DeploymentPermissionError,
    DeploymentPreconditionError,
    DeploymentProvider,
    DeploymentRateLimitError,
    DeploymentRepositoryMissingError,
    DeploymentResourceNotFoundError,
    DeploymentStatus,
    EnvironmentVariable,
    PortSpec,
    ProjectDeployment,
    RailwayAccountNotLinkedError,
    RailwayApiError,
    RailwayAuthenticationError,
    RailwayConfigurationError,
    RailwayPermissionError,
    RailwayPreconditionError,
    RailwayRateLimitError,
    RailwayRepositoryMissingError,
    RailwayResourceNotFoundError,
    UserDeploymentIntegration,
    VolumeConfig,
)
from kosmo.contracts.sdd.ids import ProjectId, UserId


@pytest.mark.unit
def test_deployment_enums() -> None:
    # Arrange & Act & Assert
    assert DeploymentProvider.RAILWAY.value == "railway"
    assert DeploymentStatus.NOT_CREATED.value == "not_created"
    assert DeploymentStatus.BUILDING.value == "building"
    assert DeploymentStatus.PUBLISHED.value == "published"
    assert DeploymentStatus.FAILED.value == "failed"


@pytest.mark.unit
def test_volume_config_creation() -> None:
    # Arrange & Act
    vol1 = VolumeConfig(mount_path="/data/db.sqlite")
    vol2 = VolumeConfig(mount_path="/data", size_mb=1024)

    # Assert
    assert vol1.mount_path == "/data/db.sqlite"
    assert vol1.size_mb is None
    assert vol2.mount_path == "/data"
    assert vol2.size_mb == 1024


@pytest.mark.unit
def test_port_spec_creation() -> None:
    # Arrange & Act
    port1 = PortSpec(port=3000)
    port2 = PortSpec(port=8000, protocol="https")

    # Assert
    assert port1.port == 3000
    assert port1.protocol == "http"
    assert port2.port == 8000
    assert port2.protocol == "https"


@pytest.mark.unit
def test_environment_variable_creation() -> None:
    # Arrange & Act
    env1 = EnvironmentVariable(key="NODE_ENV", value="production")
    env2 = EnvironmentVariable(key="DATABASE_URL", value="sqlite:///data/db.sqlite", is_secret=True)

    # Assert
    assert env1.key == "NODE_ENV"
    assert env1.value == "production"
    assert env1.is_secret is False
    assert env2.is_secret is True


@pytest.mark.unit
def test_deployment_oauth_token_creation() -> None:
    # Arrange & Act
    token = DeploymentOAuthToken(
        access_token="railway_access_token_123",
        token_type="bearer",
        refresh_token="railway_refresh_token_456",
        expires_in=3600,
    )

    # Assert
    assert token.access_token == "railway_access_token_123"
    assert token.token_type == "bearer"
    assert token.refresh_token == "railway_refresh_token_456"
    assert token.expires_in == 3600


@pytest.mark.unit
def test_user_deployment_integration_defaults() -> None:
    # Arrange
    user_id = UserId("usr_01TEST00000000000000000")

    # Act
    integration = UserDeploymentIntegration(
        user_id=user_id,
        provider=DeploymentProvider.RAILWAY,
        encrypted_token="enc_token_123",
    )

    # Assert
    assert integration.user_id == user_id
    assert integration.provider == DeploymentProvider.RAILWAY
    assert integration.encrypted_token == "enc_token_123"
    assert integration.provider_username is None
    assert isinstance(integration.updated_at, datetime)


@pytest.mark.unit
def test_project_deployment_creation() -> None:
    # Arrange
    project_id = ProjectId("prj_01TEST00000000000000000")
    deployed_at = datetime(2026, 8, 31, 12, 0, 0, tzinfo=UTC)

    # Act
    deployment = ProjectDeployment(
        project_id=project_id,
        provider=DeploymentProvider.RAILWAY,
        service_id="srv_railway_999",
        public_url="https://app.up.railway.app",
        status=DeploymentStatus.PUBLISHED,
        build_logs_url="https://railway.com/project/p1/service/s1/logs",
        last_deployed_at=deployed_at,
        error_message=None,
        volumes=(VolumeConfig(mount_path="/data"),),
        ports=(PortSpec(port=3000),),
        env_vars=(EnvironmentVariable(key="NODE_ENV", value="production"),),
    )

    # Assert
    assert deployment.project_id == project_id
    assert deployment.provider == DeploymentProvider.RAILWAY
    assert deployment.service_id == "srv_railway_999"
    assert deployment.public_url == "https://app.up.railway.app"
    assert deployment.status == DeploymentStatus.PUBLISHED
    assert deployment.build_logs_url == "https://railway.com/project/p1/service/s1/logs"
    assert deployment.last_deployed_at == deployed_at
    assert len(deployment.volumes) == 1
    assert len(deployment.ports) == 1
    assert len(deployment.env_vars) == 1


@pytest.mark.unit
def test_deployment_exception_hierarchy() -> None:
    # Arrange & Act & Assert
    assert issubclass(DeploymentAuthenticationError, DeploymentApiError)
    assert issubclass(DeploymentPermissionError, DeploymentApiError)
    assert issubclass(DeploymentResourceNotFoundError, DeploymentApiError)
    assert issubclass(DeploymentRateLimitError, DeploymentApiError)
    assert issubclass(DeploymentConfigurationError, DeploymentApiError)
    assert issubclass(DeploymentPreconditionError, DeploymentApiError)
    assert issubclass(DeploymentAccountNotLinkedError, DeploymentPreconditionError)
    assert issubclass(DeploymentRepositoryMissingError, DeploymentPreconditionError)

    # Aliases
    assert RailwayApiError is DeploymentApiError
    assert RailwayAuthenticationError is DeploymentAuthenticationError
    assert RailwayPermissionError is DeploymentPermissionError
    assert RailwayResourceNotFoundError is DeploymentResourceNotFoundError
    assert RailwayRateLimitError is DeploymentRateLimitError
    assert RailwayConfigurationError is DeploymentConfigurationError
    assert RailwayPreconditionError is DeploymentPreconditionError
    assert RailwayAccountNotLinkedError is DeploymentAccountNotLinkedError
    assert RailwayRepositoryMissingError is DeploymentRepositoryMissingError
