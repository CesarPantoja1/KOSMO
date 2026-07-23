from __future__ import annotations

import pytest

from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId
from kosmo.contracts.sdd.repositories import ActivityDiagramRepository
from tests.factories import a_diagrama_actividad, a_feature_id


class InMemoryActivityDiagramRepository:
    def __init__(self) -> None:
        self._diagrams: dict[str, DiagramaActividad] = {}

    async def save(self, diagram: DiagramaActividad) -> DiagramaActividad:
        self._diagrams[str(diagram.feature_id)] = diagram
        return diagram

    async def by_feature_id(self, feature_id: FeatureId) -> DiagramaActividad | None:
        return self._diagrams.get(str(feature_id))

    async def exists(self, feature_id: FeatureId) -> bool:
        return str(feature_id) in self._diagrams


@pytest.mark.unit
class TestActivityDiagramRepositoryContract:
    async def test_save_and_retrieve_diagram(self) -> None:
        # Arrange
        repository: ActivityDiagramRepository = InMemoryActivityDiagramRepository()
        diagram = a_diagrama_actividad()

        # Act
        saved = await repository.save(diagram)
        retrieved = await repository.by_feature_id(diagram.feature_id)

        # Assert
        assert saved is diagram
        assert retrieved is diagram
        assert retrieved.id == diagram.id
        assert retrieved.feature_id == diagram.feature_id
        assert retrieved.diagram_syntax == diagram.diagram_syntax

    async def test_by_feature_id_returns_none_when_not_found(self) -> None:
        # Arrange
        repository: ActivityDiagramRepository = InMemoryActivityDiagramRepository()

        # Act
        result = await repository.by_feature_id(FeatureId("feat_nonexistent"))

        # Assert
        assert result is None

    async def test_exists_returns_false_when_no_diagram(self) -> None:
        # Arrange
        repository: ActivityDiagramRepository = InMemoryActivityDiagramRepository()

        # Act
        result = await repository.exists(FeatureId("feat_no_diagram"))

        # Assert
        assert result is False

    async def test_save_overwrites_existing_diagram(self) -> None:
        # Arrange
        repository: ActivityDiagramRepository = InMemoryActivityDiagramRepository()
        feature_id = a_feature_id()
        first = a_diagrama_actividad(
            diagram_id=ActivityDiagramId("dia_first"),
            feature_id=feature_id,
            diagram_syntax="@startuml\n:First;\n@enduml",
        )
        second = a_diagrama_actividad(
            diagram_id=ActivityDiagramId("dia_second"),
            feature_id=feature_id,
            diagram_syntax="@startuml\n:Second;\n@enduml",
        )
        await repository.save(first)

        # Act
        await repository.save(second)
        exists = await repository.exists(feature_id)
        retrieved = await repository.by_feature_id(feature_id)

        # Assert
        assert exists is True
        assert retrieved is not None
        assert retrieved.id == second.id
        assert retrieved.diagram_syntax == "@startuml\n:Second;\n@enduml"
