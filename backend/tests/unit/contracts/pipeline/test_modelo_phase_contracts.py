from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from kosmo.contracts.pipeline.phase_contexts import ModeloPhaseContext
from kosmo.contracts.pipeline.phase_outputs import (
    GenerationMetadata,
    ModeloPhaseOutput,
    ValidationResult,
)
from kosmo.contracts.sdd.ids import FeatureId


@pytest.mark.unit
class TestModeloPhaseContext:
    def test_create_context_with_valid_data(self) -> None:
        # Arrange
        feature_id = FeatureId("feat_01KT01FABRICATED01")
        ears_requirements = "## Requisitos\n\nREQ-3.1: El sistema debe..."

        # Act
        context = ModeloPhaseContext(
            feature_id=feature_id,
            ears_requirements=ears_requirements,
        )

        # Assert
        assert context.feature_id == feature_id
        assert context.ears_requirements == ears_requirements

    def test_user_preferences_defaults_to_empty_list(self) -> None:
        # Arrange
        feature_id = FeatureId("feat_01KT01FABRICATED01")

        # Act
        context = ModeloPhaseContext(
            feature_id=feature_id,
            ears_requirements="REQ-1.1",
        )

        # Assert
        assert context.user_preferences == []

    def test_is_frozen_raises_on_mutation_attempt(self) -> None:
        # Arrange
        context = ModeloPhaseContext(
            feature_id=FeatureId("feat_01KT01FABRICATED01"),
            ears_requirements="REQ-1.1",
        )

        # Act / Assert
        with pytest.raises(FrozenInstanceError):
            context.ears_requirements = "changed"  # type: ignore[misc]


@pytest.mark.unit
class TestModeloPhaseOutput:
    def test_create_output_with_valid_data(self) -> None:
        # Arrange
        feature_id = FeatureId("feat_01KT01FABRICATED01")
        diagram_syntax = "@startuml\nstart\n:Do something;\nstop\n@enduml"
        validation = ValidationResult(is_valid=True)
        metadata = GenerationMetadata(llm_calls=1, total_tokens=50)

        # Act
        output = ModeloPhaseOutput(
            feature_id=feature_id,
            diagram_syntax=diagram_syntax,
            validation_result=validation,
            generation_metadata=metadata,
        )

        # Assert
        assert output.feature_id == feature_id
        assert output.diagram_syntax == diagram_syntax
        assert output.validation_result is validation
        assert output.generation_metadata is metadata

    def test_create_output_with_validation_errors(self) -> None:
        # Arrange
        feature_id = FeatureId("feat_01KT01FABRICATED01")
        validation = ValidationResult(
            is_valid=False,
            errors=["Sintaxis invalida: falta nodo de inicio"],
        )

        # Act
        output = ModeloPhaseOutput(
            feature_id=feature_id,
            diagram_syntax="@startuml\n:Missing start;\n@enduml",
            validation_result=validation,
            generation_metadata=GenerationMetadata(retry_count=1),
        )

        # Assert
        assert output.validation_result.is_valid is False
        assert "Sintaxis invalida" in output.validation_result.errors[0]

    def test_is_frozen_raises_on_mutation_attempt(self) -> None:
        # Arrange
        output = ModeloPhaseOutput(
            feature_id=FeatureId("feat_01KT01FABRICATED01"),
            diagram_syntax="@startuml\nstart\nstop\n@enduml",
            validation_result=ValidationResult(is_valid=True),
            generation_metadata=GenerationMetadata(),
        )

        # Act / Assert
        with pytest.raises(FrozenInstanceError):
            output.diagram_syntax = "changed"  # type: ignore[misc]
