import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.pipeline.kosmo_agent import KOSMOAgent
from kosmo.contracts.pipeline.phase_contexts import DiscoveryPhaseContext
from kosmo.contracts.pipeline.phase_outputs import (
    DiscoveryPhaseOutput,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.pipeline.tool_registry import ToolRegistry
from tests.unit.conftest import (
    DISCOVERY_VALID,
    StubStructuredLLMClient,
    make_discovery_document,
    make_discovery_mode,
)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_kosmo_agent_execute_single_step_success() -> None:
    # Arrange
    llm = StubStructuredLLMClient(responses=[make_discovery_document(DISCOVERY_VALID)])
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
    assert result.generation_metadata.retry_count == 0
    assert llm.call_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_kosmo_agent_execute_retries_on_validation_failure() -> None:
    # Arrange
    invalid_doc = make_discovery_document("## Vision del producto\n\nAPI REST")
    valid_doc = make_discovery_document(DISCOVERY_VALID)
    llm = StubStructuredLLMClient(responses=[invalid_doc, valid_doc])
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
    assert result.generation_metadata.retry_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_kosmo_agent_execute_stops_at_max_iterations() -> None:
    # Arrange
    always_invalid = make_discovery_document("## Test\n\nContenido insuficiente")
    llm = StubStructuredLLMClient(responses=[always_invalid, always_invalid, always_invalid])
    registry = ToolRegistry()
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
async def test_kosmo_agent_raises_when_mode_missing() -> None:
    # Arrange
    llm = StubStructuredLLMClient()
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


@pytest.mark.asyncio
@pytest.mark.unit
async def test_kosmo_agent_raises_when_llm_fails() -> None:
    # Arrange
    class FailingLLMClient:
        async def complete(self, prompt, temperature=0.3, max_tokens=4096):  # noqa: ARG002
            msg = "LLM error"
            raise RuntimeError(msg)

        async def complete_json(self, prompt, temperature=0.1, max_tokens=4096):  # noqa: ARG002
            msg = "LLM error"
            raise RuntimeError(msg)

        async def complete_typed(self, prompt, output_type, temperature=0.1, max_tokens=4096):  # noqa: ARG002
            msg = "LLM error"
            raise RuntimeError(msg)

    llm = FailingLLMClient()
    registry = ToolRegistry()
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
    assert result.generation_metadata.llm_calls == 0
    assert result.discovery_document.nodes == []
