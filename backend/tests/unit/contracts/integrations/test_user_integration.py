from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kosmo.contracts.integrations.user_integration import (
    IntegrationProvider,
    UserIntegration,
)
from kosmo.contracts.sdd.ids import UserId


@pytest.mark.unit
def test_user_integration_creation_default_fields() -> None:
    # Arrange
    user_id = UserId("usr_01J00000000000000000000000")
    token = "gasp_encrypted_token_123"

    # Act
    integration = UserIntegration(
        user_id=user_id,
        provider=IntegrationProvider.GITHUB,
        encrypted_access_token=token,
    )

    # Assert
    assert integration.user_id == user_id
    assert integration.provider == IntegrationProvider.GITHUB
    assert integration.encrypted_access_token == token
    assert integration.account_name is None
    assert integration.encrypted_refresh_token is None
    assert integration.scopes == []
    assert isinstance(integration.created_at, datetime)
    assert isinstance(integration.updated_at, datetime)


@pytest.mark.unit
def test_user_integration_creation_all_fields() -> None:
    # Arrange
    user_id = UserId("usr_01J00000000000000000000000")
    created = datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC)
    updated = datetime(2026, 8, 21, 14, 30, 0, tzinfo=UTC)

    # Act
    integration = UserIntegration(
        user_id=user_id,
        provider=IntegrationProvider.RAILWAY,
        encrypted_access_token="railway_token_enc",
        account_name="my-railway-account",
        encrypted_refresh_token="railway_refresh_enc",
        scopes=["read", "write"],
        created_at=created,
        updated_at=updated,
    )

    # Assert
    assert integration.user_id == user_id
    assert integration.provider == IntegrationProvider.RAILWAY
    assert integration.encrypted_access_token == "railway_token_enc"
    assert integration.account_name == "my-railway-account"
    assert integration.encrypted_refresh_token == "railway_refresh_enc"
    assert integration.scopes == ["read", "write"]
    assert integration.created_at == created
    assert integration.updated_at == updated


@pytest.mark.unit
def test_integration_provider_values() -> None:
    # Arrange & Act & Assert
    assert IntegrationProvider.GITHUB.value == "github"
    assert IntegrationProvider.RAILWAY.value == "railway"
    assert IntegrationProvider("github") == IntegrationProvider.GITHUB
    assert IntegrationProvider("railway") == IntegrationProvider.RAILWAY
