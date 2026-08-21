"""Tests unitarios para el router MCP de KOSMO.

Verifica que las tools get_requirements y get_activity_diagram retornan
los datos correctos desde los repositorios o errores 404 cuando no existen.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId
from kosmo.infrastructure.api.routers.mcp import router as mcp_router
from tests.unit.fakes import InMemoryActivityDiagramRepository, InMemoryRequirementRepository


def _build_app(
    *,
    requirement_repo: InMemoryRequirementRepository | None = None,
    diagram_repo: InMemoryActivityDiagramRepository | None = None,
) -> TestClient:
    """Monta una mini-app FastAPI con el router MCP y repositorios fake."""
    app = FastAPI()
    app.include_router(mcp_router)

    req_repo = requirement_repo or InMemoryRequirementRepository()
    dia_repo = diagram_repo or InMemoryActivityDiagramRepository()
    app.state.requirement_repo = req_repo
    app.state.diagram_repo = dia_repo

    return TestClient(app)


_FEATURE_ID = "feat_01KT01FABRICATED01"
_EARS_MARKDOWN = """\
### REQ-1.1 Registrar gastos

**Ubicuo**

El sistema shall registrar un gasto con monto, fecha y descripción.

**Criterios de aceptación**

**Escenario:** Gasto válido
- **Dado** que el usuario tiene una cuenta activa
- **Cuando** registra un gasto de $50.00
- **Entonces** el sistema almacena el gasto con dos decimales
"""
_PLANTUML = "@startuml\nstart\n:Registrar gasto;\nstop\n@enduml"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_requirements_returns_markdown_for_existing_feature() -> None:
    """Happy path: requisitos existentes se retornan como markdown."""
    # Arrange
    req_repo = InMemoryRequirementRepository()
    await req_repo.save(FeatureId(_FEATURE_ID), _EARS_MARKDOWN)
    client = _build_app(requirement_repo=req_repo)

    # Act
    response = client.post("/mcp/tools/get_requirements", json={"feature_id": _FEATURE_ID})

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["content"] == _EARS_MARKDOWN
    assert body["feature_id"] == _FEATURE_ID


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_activity_diagram_returns_plantuml_for_existing_feature() -> None:
    """Happy path: diagrama existente se retorna como PlantUML syntax."""
    # Arrange
    from kosmo.contracts.sdd.activity_diagram import DiagramaActividad

    diagram_repo = InMemoryActivityDiagramRepository()
    diagram = DiagramaActividad(
        id=ActivityDiagramId("dia_01KT01FABRICATED01"),
        feature_id=FeatureId(_FEATURE_ID),
        diagram_syntax=_PLANTUML,
    )
    await diagram_repo.save(diagram)
    client = _build_app(diagram_repo=diagram_repo)

    # Act
    response = client.post("/mcp/tools/get_activity_diagram", json={"feature_id": _FEATURE_ID})

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["content"] == _PLANTUML
    assert body["feature_id"] == _FEATURE_ID


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_requirements_returns_404_when_feature_has_no_requirements() -> None:
    """Error path: feature sin requisitos retorna 404 con detalle RFC 7807."""
    # Arrange
    client = _build_app()

    # Act
    response = client.post("/mcp/tools/get_requirements", json={"feature_id": _FEATURE_ID})

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body
    assert _FEATURE_ID in body["detail"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_activity_diagram_returns_404_when_feature_has_no_diagram() -> None:
    """Error path: feature sin diagrama retorna 404 con detalle."""
    # Arrange
    client = _build_app()

    # Act
    response = client.post("/mcp/tools/get_activity_diagram", json={"feature_id": _FEATURE_ID})

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body
    assert _FEATURE_ID in body["detail"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_requirements_returns_empty_markdown_preserved() -> None:
    """Edge case: markdown vacío pero existente se retorna tal cual."""
    # Arrange
    req_repo = InMemoryRequirementRepository()
    await req_repo.save(FeatureId(_FEATURE_ID), "")
    client = _build_app(requirement_repo=req_repo)

    # Act
    response = client.post("/mcp/tools/get_requirements", json={"feature_id": _FEATURE_ID})

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["content"] == ""
    assert body["feature_id"] == _FEATURE_ID
