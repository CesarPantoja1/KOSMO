import pytest

from kosmo.application.pipeline.kosmo_agent import KOSMOAgent
from kosmo.contracts.pipeline.orchestrator_ports import Skill
from kosmo.contracts.pipeline.phase_contexts import DiscoveryPhaseContext
from kosmo.contracts.pipeline.phase_outputs import (
    DiscoveryPhaseOutput,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.pipeline.skill_registry import SkillRegistry
from kosmo.domain.pipeline.tool_registry import ToolRegistry
from tests.unit.conftest import (
    DISCOVERY_VALID,
    StubStructuredLLMClient,
    make_discovery_document,
    make_discovery_mode,
)


def _make_agent(llm, max_iterations=3, memory=None):
    registry = ToolRegistry()
    skill_reg = SkillRegistry()
    skill_reg.register(
        Skill(
            name="discovery_generate",
            description="Test skill",
            phase=SpecPhase.DESCUBRIMIENTO,
            mode=make_discovery_mode(),  # type: ignore[reportArgumentType]
        )
    )
    return KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=max_iterations,
        skill_registry=skill_reg,
        memory=memory,  # type: ignore[reportArgumentType]
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_kosmo_agent_execute_single_step_success() -> None:
    # Arrange
    llm = StubStructuredLLMClient(responses=[make_discovery_document(DISCOVERY_VALID)])
    agent = _make_agent(llm)

    # Act
    result = await agent.execute_with_skill(
        skill_name="discovery_generate",
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
    agent = _make_agent(llm)

    # Act
    result = await agent.execute_with_skill(
        skill_name="discovery_generate",
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
    agent = _make_agent(llm, max_iterations=2)

    # Act
    result = await agent.execute_with_skill(
        skill_name="discovery_generate",
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
    )

    # Assert
    assert result.validation_result.is_valid is False
    assert llm.call_count == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_kosmo_agent_raises_when_skill_not_found() -> None:
    # Arrange
    llm = StubStructuredLLMClient()
    agent = _make_agent(llm)

    # Act & Assert
    with pytest.raises(ValueError, match="Skill "):
        await agent.execute_with_skill(
            skill_name="nonexistent_skill",
            context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_kosmo_agent_raises_when_no_skill_registry() -> None:
    # Arrange
    llm = StubStructuredLLMClient()
    registry = ToolRegistry()
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="SkillRegistry"):
        await agent.execute_with_skill(
            skill_name="discovery_generate",
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
    agent = _make_agent(llm, max_iterations=2)

    # Act
    result = await agent.execute_with_skill(
        skill_name="discovery_generate",
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
    )

    # Assert
    assert result.validation_result.is_valid is False
    assert result.generation_metadata.llm_calls == 0
    assert result.discovery_document.nodes == []
