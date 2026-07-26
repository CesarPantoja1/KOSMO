import importlib

import pytest
from fastapi.testclient import TestClient

app = importlib.import_module("kosmo.infrastructure.api.main").app


@pytest.mark.unit
def test_health_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
