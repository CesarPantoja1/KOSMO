from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from kosmo.contracts.codegen import OpenCodeEvent, OpenCodeEventType
from kosmo.infrastructure.api.main import app


@pytest.fixture
def mock_broker():
    with patch("kosmo.infrastructure.api.routers.implementations.broker") as mock:
        yield mock


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def valid_token_headers():
    # In KOSMO, we might need a real-ish token, or we can mock get_principal.
    # Usually we mock get_principal or the route depends on it.
    # For unit tests, we can just override the dependency:
    from unittest.mock import MagicMock

    from kosmo.contracts.auth import Principal
    from kosmo.infrastructure.api.dependencies.auth import get_principal
    from kosmo.infrastructure.api.dependencies.container import get_container

    app.dependency_overrides[get_principal] = lambda: Principal(subject="usr_123")
    app.dependency_overrides[get_container] = lambda: MagicMock()
    return {"Authorization": "Bearer mock"}


def test_start_implementation(client: TestClient, mock_broker, valid_token_headers: dict[str, str]) -> None:
    # Arrange
    payload = {
        "feature_id": "feat_01ULXGXXXX",
        "max_retries": 3,
    }

    # Act
    response = client.post(
        "/api/v1/implementations",
        json=payload,
        headers=valid_token_headers,
    )

    # Assert
    assert response.status_code == 202
    data = response.json()
    assert "implementation_id" in data
    assert data["implementation_id"] == "impl_feat_01ULXGXXXX"

    # Verificar que se llamó al broker
    mock_broker.start_implementation.assert_called_once()
    kwargs = mock_broker.start_implementation.call_args.kwargs
    assert kwargs["implementation_id"] == "impl_feat_01ULXGXXXX"


def test_stream_implementation_events(client: TestClient, mock_broker, valid_token_headers: dict[str, str]) -> None:
    # Arrange
    async def fake_subscribe(*_args, **_kwargs) -> AsyncGenerator[OpenCodeEvent]:
        yield OpenCodeEvent(event_type=OpenCodeEventType.PLAN_PROGRESS, session_id="sess_123", data={"msg": "hello"})
        yield OpenCodeEvent(event_type=OpenCodeEventType.DONE, session_id="sess_123", data={})

    mock_broker.subscribe.side_effect = fake_subscribe

    # Act
    with client.stream("GET", "/api/v1/implementations/impl_123/events", headers=valid_token_headers) as response:
        assert response.status_code == 200

        content = response.read().decode()

    # Assert
    assert "event: plan_progress" in content
    assert '"event_type": "plan_progress"' in content
    assert '"msg":"hello"' in content.replace(" ", "")
    assert "event: done" in content
