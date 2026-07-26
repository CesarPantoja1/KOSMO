from __future__ import annotations

from typing import Any

import pytest

from kosmo.application.modelo.generate_diagram import (
    GenerateActivityDiagramUseCase,
    GenerateDiagramInput,
    GenerateDiagramOutput,
)
from kosmo.contracts.pipeline.phase_outputs import (
    GenerationMetadata,
    ModeloPhaseOutput,
    ValidationResult,
)
from kosmo.contracts.sdd.errors import (
    FeatureNotFoundError,
    LLMInvocationError,
    RequirementsNotFoundError,
)
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from tests.unit.fakes import InMemoryActivityDiagramRepository, InMemoryFeatureRepository, InMemoryRequirementRepository


class MockAgent:
    def __init__(self, output: Any) -> None:
        self._output = output

    async def execute_with_skill(
        self, skill_name: str, context: Any, *, project_id: Any = None, user_instructions: str | None = None
    ) -> Any:  # noqa: ARG002
        return self._output


def _make_feature(feature_id: str = "feat_01") -> Feature:
    return Feature(
        id=FeatureId(feature_id),
        number=1,
        title="Test Feature",
        slug="test-feature",
        description="Test feature description",
        project_id=ProjectId("prj_01"),
    )


def _make_ears_requirements_markdown() -> str:
    return """### REQ-1.1

| Campo | Contenido |
|-------|-----------|
| **Patrón** | Requisitos Ubicuos |
| **Enunciado** | El sistema debe procesar pagos de forma segura |

#### Criterios de Aceptación

**Escenario: Pago exitoso**

- **Dado** que un usuario autenticado
- **Cuando** realiza un pago válido
- **Entonces** el pago se procesa correctamente
"""


_VALID_DIAGRAM_SYNTAX = (
    "@startuml\n"
    "start\n"
    ":Procesar pago;\n"
    "if (¿Pago válido?) then (sí)\n"
    "  :Confirmar;\n"
    "else (no)\n"
    "  :Rechazar;\n"
    "endif\n"
    "stop\n"
    "@enduml"
)


def _make_input(project_id: str = "prj_01", feature_id: str = "feat_01") -> GenerateDiagramInput:
    return GenerateDiagramInput(project_id=ProjectId(project_id), feature_id=FeatureId(feature_id))


def _make_valid_modelo_output(feature_id: str = "feat_01") -> ModeloPhaseOutput:
    return ModeloPhaseOutput(
        feature_id=FeatureId(feature_id),
        diagram_syntax=_VALID_DIAGRAM_SYNTAX,
        validation_result=ValidationResult(is_valid=True),
        generation_metadata=GenerationMetadata(llm_calls=1),
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_diagram_success() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    feature = _make_feature()
    await feature_repo.save(feature)
    await req_repo.save(FeatureId("feat_01"), _make_ears_requirements_markdown())
    agent = MockAgent(output=_make_valid_modelo_output())
    use_case = GenerateActivityDiagramUseCase(
        feature_repo=feature_repo,
        requirement_repo=req_repo,
        diagram_repo=diagram_repo,
        agent=agent,
    )

    # Act
    result = await use_case.execute(_make_input())

    # Assert
    assert isinstance(result, GenerateDiagramOutput)
    assert result.diagram.feature_id == FeatureId("feat_01")
    assert "Procesar pago" in result.diagram.diagram_syntax
    assert result.phase_output.feature_id == FeatureId("feat_01")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_diagram_raises_feature_not_found() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    agent = MockAgent(output=_make_valid_modelo_output())
    use_case = GenerateActivityDiagramUseCase(
        feature_repo=feature_repo,
        requirement_repo=req_repo,
        diagram_repo=diagram_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(FeatureNotFoundError) as exc_info:
        await use_case.execute(_make_input(feature_id="feat_missing"))
    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_diagram_raises_requirements_not_found() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    feature = _make_feature()
    await feature_repo.save(feature)
    agent = MockAgent(output=_make_valid_modelo_output())
    use_case = GenerateActivityDiagramUseCase(
        feature_repo=feature_repo,
        requirement_repo=req_repo,
        diagram_repo=diagram_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(RequirementsNotFoundError) as exc_info:
        await use_case.execute(_make_input())
    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_diagram_raises_llm_invocation_on_agent_failure() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    feature = _make_feature()
    await feature_repo.save(feature)
    await req_repo.save(FeatureId("feat_01"), _make_ears_requirements_markdown())

    class FailingAgent:
        async def execute_with_skill(
            self, skill_name: str, context: Any, *, project_id: Any = None, user_instructions: str | None = None
        ) -> Any:  # noqa: ARG002
            raise RuntimeError("LLM service unavailable")

    agent = FailingAgent()
    use_case = GenerateActivityDiagramUseCase(
        feature_repo=feature_repo,
        requirement_repo=req_repo,
        diagram_repo=diagram_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(LLMInvocationError) as exc_info:
        await use_case.execute(_make_input())
    assert exc_info.value.problem.status == 502


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_diagram_raises_on_invalid_output_type() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    feature = _make_feature()
    await feature_repo.save(feature)
    await req_repo.save(FeatureId("feat_01"), _make_ears_requirements_markdown())
    agent = MockAgent(output="unexpected string instead of ModeloPhaseOutput")
    use_case = GenerateActivityDiagramUseCase(
        feature_repo=feature_repo,
        requirement_repo=req_repo,
        diagram_repo=diagram_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(LLMInvocationError) as exc_info:
        await use_case.execute(_make_input())
    assert exc_info.value.problem.status == 502
    assert "ModeloPhaseOutput" in exc_info.value.problem.detail


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_diagram_persists_diagram() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    feature = _make_feature()
    await feature_repo.save(feature)
    await req_repo.save(FeatureId("feat_01"), _make_ears_requirements_markdown())
    agent = MockAgent(output=_make_valid_modelo_output())
    use_case = GenerateActivityDiagramUseCase(
        feature_repo=feature_repo,
        requirement_repo=req_repo,
        diagram_repo=diagram_repo,
        agent=agent,
    )

    # Act
    result = await use_case.execute(_make_input())

    # Assert
    persisted = await diagram_repo.by_feature_id(FeatureId("feat_01"))
    assert persisted is not None
    assert persisted.id == result.diagram.id
    assert persisted.feature_id == FeatureId("feat_01")
    assert "Procesar pago" in persisted.diagram_syntax


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_diagram_raises_on_validation_failure() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    feature = _make_feature()
    await feature_repo.save(feature)
    await req_repo.save(FeatureId("feat_01"), _make_ears_requirements_markdown())
    invalid_output = ModeloPhaseOutput(
        feature_id=FeatureId("feat_01"),
        diagram_syntax="",
        validation_result=ValidationResult(is_valid=False, errors=["El diagrama debe comenzar con @startuml"]),
        generation_metadata=GenerationMetadata(llm_calls=1),
    )
    agent = MockAgent(output=invalid_output)
    use_case = GenerateActivityDiagramUseCase(
        feature_repo=feature_repo,
        requirement_repo=req_repo,
        diagram_repo=diagram_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(LLMInvocationError) as exc_info:
        await use_case.execute(_make_input())
    assert exc_info.value.problem.status == 502
    assert "El diagrama debe comenzar con @startuml" in exc_info.value.problem.detail


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_diagram_raises_on_empty_diagram_syntax() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    feature = _make_feature()
    await feature_repo.save(feature)
    await req_repo.save(FeatureId("feat_01"), _make_ears_requirements_markdown())
    empty_output = ModeloPhaseOutput(
        feature_id=FeatureId("feat_01"),
        diagram_syntax="",
        validation_result=ValidationResult(is_valid=True),
        generation_metadata=GenerationMetadata(llm_calls=1),
    )
    agent = MockAgent(output=empty_output)
    use_case = GenerateActivityDiagramUseCase(
        feature_repo=feature_repo,
        requirement_repo=req_repo,
        diagram_repo=diagram_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(LLMInvocationError) as exc_info:
        await use_case.execute(_make_input())
    assert exc_info.value.problem.status == 502
