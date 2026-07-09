from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.pipeline.kosmo_agent import KOSMOAgent
from kosmo.contracts.pipeline.phase_contexts import DiscoveryPhaseContext
from kosmo.contracts.pipeline.phase_outputs import DiscoveryPhaseOutput
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.pipeline.tool_registry import ToolRegistry
from kosmo.infrastructure.persistence.memory.in_memory_store import (
    InMemoryAgentSessionStore,
)
from tests.factories import a_project_id
from tests.unit.conftest import (
    DISCOVERY_VALID,
    StubReactLLMClient,
    make_discovery_mode,
    make_valid_discovery_json,
)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_agent_saves_session_on_successful_completion() -> None:
    # Arrange
    llm = StubReactLLMClient(responses=[make_valid_discovery_json(DISCOVERY_VALID)])
    registry = ToolRegistry()
    store = InMemoryAgentSessionStore()
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=3,
        memory=store,  # type: ignore[reportArgumentType]
    )
    agent._modes[SpecPhase.DESCUBRIMIENTO] = make_discovery_mode()  # type: ignore[reportPrivateUsage]
    project_id = a_project_id()

    # Act
    result = await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
        project_id=project_id,
    )

    # Assert
    assert isinstance(result, DiscoveryPhaseOutput)
    assert result.validation_result.is_valid is True
    sessions = await store.list_sessions(project_id)
    assert len(sessions) == 1
    saved = sessions[0]
    assert saved.session_type == "generation"
    assert saved.phase == SpecPhase.DESCUBRIMIENTO
    assert saved.is_completed is True
    assert saved.total_llm_calls == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_agent_injects_context_from_previous_sessions() -> None:
    # Arrange
    llm = StubReactLLMClient(responses=[make_valid_discovery_json(DISCOVERY_VALID)])
    registry = ToolRegistry()
    store = InMemoryAgentSessionStore()
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=3,
        memory=store,  # type: ignore[reportArgumentType]
    )
    agent._modes[SpecPhase.DESCUBRIMIENTO] = make_discovery_mode()  # type: ignore[reportPrivateUsage]
    project_id = a_project_id()

    # First execution to create a previous session
    await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
        project_id=project_id,
    )

    # Act - second execution should have context from first
    result = await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
        project_id=project_id,
    )

    # Assert
    assert result.validation_result.is_valid is True
    sessions = await store.list_sessions(project_id)
    assert len(sessions) == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_agent_without_memory_works_normally() -> None:
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
    assert agent.memory is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_agent_with_memory_but_no_project_id_does_not_save() -> None:
    # Arrange
    llm = StubReactLLMClient(responses=[make_valid_discovery_json(DISCOVERY_VALID)])
    registry = ToolRegistry()
    store = InMemoryAgentSessionStore()
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=3,
        memory=store,  # type: ignore[reportArgumentType]
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
    sessions = await store.list_sessions(a_project_id())
    assert len(sessions) == 0


@pytest.mark.unit
@pytest.mark.parametrize(
    "user_instructions,expected_session_type",
    [
        ("hazlo mas conciso", "refinement"),
        (None, "generation"),
    ],
)
@pytest.mark.asyncio
async def test_agent_saves_correct_session_type(
    user_instructions: str | None,
    expected_session_type: str,
) -> None:
    # Arrange
    llm = StubReactLLMClient(responses=[make_valid_discovery_json(DISCOVERY_VALID)])
    registry = ToolRegistry()
    store = InMemoryAgentSessionStore()
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=3,
        memory=store,  # type: ignore[reportArgumentType]
    )
    agent._modes[SpecPhase.DESCUBRIMIENTO] = make_discovery_mode()  # type: ignore[reportPrivateUsage]
    project_id = a_project_id()

    # Act
    result = await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
        project_id=project_id,
        user_instructions=user_instructions,
    )

    # Assert
    assert result.validation_result.is_valid is True
    sessions = await store.list_sessions(project_id)
    assert len(sessions) == 1
    assert sessions[0].session_type == expected_session_type
    assert sessions[0].user_instructions == user_instructions


@pytest.mark.unit
@pytest.mark.parametrize(
    "project_a,project_b",
    [
        (ProjectId("prj_A"), ProjectId("prj_B")),
        (ProjectId("prj_01KT01ABC"), ProjectId("prj_01KT01DEF")),
    ],
)
@pytest.mark.asyncio
async def test_sessions_are_isolated_between_projects(
    project_a: ProjectId,
    project_b: ProjectId,
) -> None:
    # Arrange
    llm = StubReactLLMClient(
        responses=[
            make_valid_discovery_json(DISCOVERY_VALID),
            make_valid_discovery_json(DISCOVERY_VALID),
        ]
    )
    registry = ToolRegistry()
    store = InMemoryAgentSessionStore()
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=3,
        memory=store,  # type: ignore[reportArgumentType]
    )
    agent._modes[SpecPhase.DESCUBRIMIENTO] = make_discovery_mode()  # type: ignore[reportPrivateUsage]

    # Act
    await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="A", project_description="A"),
        project_id=project_a,
    )
    await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="B", project_description="B"),
        project_id=project_b,
    )

    # Assert
    sessions_a = await store.list_sessions(project_a)
    sessions_b = await store.list_sessions(project_b)
    assert len(sessions_a) == 1
    assert len(sessions_b) == 1
    assert sessions_a[0].project_id != sessions_b[0].project_id
