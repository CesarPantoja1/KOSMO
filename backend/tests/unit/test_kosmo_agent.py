import json
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.pipeline.kosmo_agent import (
    _REACT_FORMAT_INSTRUCTIONS,  # type: ignore[reportPrivateUsage]
    KOSMOAgent,
)
from kosmo.contracts.pipeline.phase_contexts import DiscoveryPhaseContext
from kosmo.contracts.pipeline.phase_outputs import (
    DiscoveryPhaseOutput,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.pipeline.tool_registry import ToolRegistry
from tests.unit.conftest import (
    DISCOVERY_VALID,
    StubReactLLMClient,
    make_discovery_mode,
    make_valid_discovery_json,
)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_kosmo_agent_execute_single_step_success() -> None:
    # Arrange
    llm = StubReactLLMClient(responses=[make_valid_discovery_json(DISCOVERY_VALID)])
    registry = ToolRegistry()
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=3,
    )
    agent._modes[SpecPhase.DESCUBRIMIENTO] = make_discovery_mode()  # type: ignore[reportPrivateUsage]

    # Act
    result = await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
    )

    # Assert
    assert isinstance(result, DiscoveryPhaseOutput)
    assert result.validation_result.is_valid is True
    assert result.generation_metadata.llm_calls == 1
    assert len(result.generation_metadata.reasoning_log) == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_kosmo_agent_execute_with_tool_call() -> None:
    # Arrange
    responses = [
        json.dumps(
            {
                "reasoning": "Necesito verificar la estructura",
                "action": "validate_structure",
                "input": {"document": DISCOVERY_VALID},
            }
        ),
        make_valid_discovery_json(DISCOVERY_VALID),
    ]
    llm = StubReactLLMClient(responses=responses)
    registry = ToolRegistry()
    registry.register(
        "validate_structure",
        lambda _: {"is_valid": True, "errors": []},
    )
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=3,
    )
    agent._modes[SpecPhase.DESCUBRIMIENTO] = make_discovery_mode()  # type: ignore[reportPrivateUsage]

    # Act
    result = await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
    )

    # Assert
    assert isinstance(result, DiscoveryPhaseOutput)
    assert result.validation_result.is_valid is True
    assert llm.call_count == 2
    assert result.generation_metadata.llm_calls == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_kosmo_agent_execute_retries_on_validation_failure() -> None:
    # Arrange
    invalid_doc = "## Vision del producto\n\nAPI REST"
    valid_doc = DISCOVERY_VALID
    responses = [
        make_valid_discovery_json(invalid_doc),
        make_valid_discovery_json(valid_doc),
    ]
    llm = StubReactLLMClient(responses=responses)
    registry = ToolRegistry()
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=3,
    )
    agent._modes[SpecPhase.DESCUBRIMIENTO] = make_discovery_mode()  # type: ignore[reportPrivateUsage]

    # Act
    result = await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
    )

    # Assert
    assert result.validation_result.is_valid is True
    assert llm.call_count == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_kosmo_agent_execute_stops_at_max_iterations() -> None:
    # Arrange
    responses = [
        json.dumps(
            {
                "reasoning": "Intento 1",
                "action": "validate_structure",
                "input": {"document": "## Test"},
            }
        ),
        json.dumps(
            {
                "reasoning": "Intento 2",
                "action": "validate_structure",
                "input": {"document": "## Test"},
            }
        ),
        json.dumps(
            {
                "reasoning": "Intento 3",
                "action": "validate_structure",
                "input": {"document": "## Test"},
            }
        ),
    ]
    llm = StubReactLLMClient(responses=responses)
    registry = ToolRegistry()
    registry.register(
        "validate_structure",
        lambda _: {"is_valid": False, "errors": ["Falta contenido"]},
    )
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=2,
    )
    agent._modes[SpecPhase.DESCUBRIMIENTO] = make_discovery_mode()  # type: ignore[reportPrivateUsage]

    # Act
    result = await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
    )

    # Assert
    assert result.validation_result.is_valid is False
    assert llm.call_count == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_kosmo_agent_execute_traces_steps() -> None:
    # Arrange
    responses = [
        json.dumps(
            {
                "reasoning": "Verificando estructura",
                "action": "validate_structure",
                "input": {"document": DISCOVERY_VALID},
            }
        ),
        make_valid_discovery_json(DISCOVERY_VALID),
    ]
    llm = StubReactLLMClient(responses=responses)
    registry = ToolRegistry()
    registry.register(
        "validate_structure",
        lambda _: {"is_valid": True, "errors": []},
    )
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=3,
    )
    agent._modes[SpecPhase.DESCUBRIMIENTO] = make_discovery_mode()  # type: ignore[reportPrivateUsage]

    # Act
    result = await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
    )

    # Assert
    assert result.generation_metadata.reasoning_log is not None
    assert len(result.generation_metadata.reasoning_log) >= 1
    assert any("validate_structure" in log for log in result.generation_metadata.reasoning_log)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_kosmo_agent_raises_when_mode_missing() -> None:
    # Arrange
    llm = StubReactLLMClient()
    registry = ToolRegistry()
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="No hay modo"):
        await agent.execute(
            phase=SpecPhase.DESCUBRIMIENTO,
            context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
        )


@pytest.mark.unit
def test_react_format_instructions_use_valid_json_examples() -> None:
    # Arrange
    text = _REACT_FORMAT_INSTRUCTIONS
    tool_example = (
        '{"reasoning": "por que necesitas esta herramienta", '
        '"action": "nombre_herramienta", "input": {"param": "valor"}}'
    )
    final_example = (
        '{"reasoning": "por que el trabajo esta completo", "final": true, "output": "documento completo en markdown"}'
    )

    # Act / Assert: los ejemplos que ve el modelo deben ser JSON válido (sin llaves dobles)
    assert "{{" not in text
    assert tool_example in text
    assert final_example in text
    assert json.loads(tool_example)["action"] == "nombre_herramienta"
    assert json.loads(final_example)["final"] is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_kosmo_agent_max_iterations_yields_empty_document_not_none() -> None:
    # Arrange
    tool_call = json.dumps(
        {
            "reasoning": "sigo verificando",
            "action": "validate_structure",
            "input": {"document": "## Test"},
        }
    )
    llm = StubReactLLMClient(responses=[tool_call, tool_call])
    registry = ToolRegistry()
    registry.register("validate_structure", lambda _: {"is_valid": False, "errors": ["x"]})
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=2,
    )
    agent._modes[SpecPhase.DESCUBRIMIENTO] = make_discovery_mode()  # type: ignore[reportPrivateUsage]

    # Act
    result = await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
    )

    # Assert
    assert result.validation_result.is_valid is False
    assert result.discovery_document.nodes == []
