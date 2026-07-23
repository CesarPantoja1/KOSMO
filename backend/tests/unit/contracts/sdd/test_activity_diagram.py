from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.errors import DiagramNotFoundError
from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId


@pytest.mark.unit
class TestDiagramaActividadEntity:
    def test_create_diagrama_actividad_with_valid_data(self) -> None:
        # Arrange
        diagram_id = ActivityDiagramId("dia_01KT01FABRICATED01")
        feature_id = FeatureId("feat_01KT01FABRICATED01")
        now = datetime.now(UTC)
        syntax = "@startuml\nstart\n:Do something;\nstop\n@enduml"

        # Act
        diagram = DiagramaActividad(
            id=diagram_id,
            feature_id=feature_id,
            diagram_syntax=syntax,
            created_at=now,
            updated_at=now,
        )

        # Assert
        assert diagram.id == diagram_id
        assert diagram.feature_id == feature_id
        assert diagram.diagram_syntax == syntax
        assert diagram.created_at == now
        assert diagram.updated_at == now

    def test_default_timestamps_are_set(self) -> None:
        # Arrange
        before = datetime.now(UTC)

        # Act
        diagram = DiagramaActividad(
            id=ActivityDiagramId("dia_01KT01FABRICATED02"),
            feature_id=FeatureId("feat_01KT01FABRICATED01"),
            diagram_syntax="@startuml\nstart\n:Step;\nstop\n@enduml",
        )

        # Assert
        assert diagram.created_at >= before
        assert diagram.updated_at >= before


@pytest.mark.unit
class TestDiagramNotFoundError:
    def test_error_construction_with_feature_id(self) -> None:
        # Arrange
        feature_id = "feat_01KT01MISSING"

        # Act
        error = DiagramNotFoundError(feature_id=feature_id)

        # Assert
        assert feature_id in str(error)
        assert error.problem.status == 404
        assert error.problem.type == "urn:kosmo:diagrams:not-found"

    def test_error_construction_with_custom_instance(self) -> None:
        # Arrange
        feature_id = "feat_custom"
        instance = "/api/v1/features/feat_custom/diagram"

        # Act
        error = DiagramNotFoundError(feature_id=feature_id, instance=instance)

        # Assert
        assert error.problem.instance == instance
        assert error.problem.status == 404
