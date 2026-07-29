from __future__ import annotations

import pytest

from kosmo.contracts.sdd.ids import FeatureId
from kosmo.infrastructure.llm.knowledge_tools import (
    build_get_diagram_for_feature,
    build_get_requirements_for_feature,
)
from tests.unit.fakes import (
    InMemoryActivityDiagramRepository,
    InMemoryRequirementRepository,
)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_requirements_returns_markdown() -> None:
    # Arrange
    repo = InMemoryRequirementRepository()
    await repo.save(FeatureId("feat_01"), "### REQ-1.1\n\n**Ubicuo**\n\nEl sistema debe procesar pagos")
    _def, handler = build_get_requirements_for_feature(repo)

    # Act
    result = await handler({"feature_id": "feat_01"})

    # Assert
    assert "REQ-1.1" in result
    assert "procesar pagos" in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_requirements_not_found() -> None:
    # Arrange
    repo = InMemoryRequirementRepository()
    _def, handler = build_get_requirements_for_feature(repo)

    # Act
    result = await handler({"feature_id": "feat_missing"})

    # Assert
    assert "no se encontraron" in result.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_requirements_missing_param() -> None:
    # Arrange
    repo = InMemoryRequirementRepository()
    _def, handler = build_get_requirements_for_feature(repo)

    # Act
    result = await handler({})

    # Assert
    assert "feature_id" in result.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_diagram_returns_plantuml() -> None:
    # Arrange
    repo = InMemoryActivityDiagramRepository()
    diagram_syntax = "@startuml\nstart\n:Accion;\nstop\n@enduml"
    from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
    from kosmo.contracts.sdd.ids import ActivityDiagramId

    await repo.save(
        DiagramaActividad(
            id=ActivityDiagramId("dia_01"),
            feature_id=FeatureId("feat_01"),
            diagram_syntax=diagram_syntax,
        )
    )
    _def, handler = build_get_diagram_for_feature(repo)

    # Act
    result = await handler({"feature_id": "feat_01"})

    # Assert
    assert "@startuml" in result
    assert "Accion" in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_diagram_not_found() -> None:
    # Arrange
    repo = InMemoryActivityDiagramRepository()
    _def, handler = build_get_diagram_for_feature(repo)

    # Act
    result = await handler({"feature_id": "feat_missing"})

    # Assert
    assert "no se encontro" in result.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_diagram_missing_param() -> None:
    # Arrange
    repo = InMemoryActivityDiagramRepository()
    _def, handler = build_get_diagram_for_feature(repo)

    # Act
    result = await handler({})

    # Assert
    assert "feature_id" in result.lower()
