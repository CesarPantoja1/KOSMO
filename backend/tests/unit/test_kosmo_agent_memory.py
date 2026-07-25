from __future__ import annotations

import pytest

from kosmo.application.pipeline.kosmo_agent import KOSMOAgent
from kosmo.contracts.pipeline.orchestrator_ports import Skill
from kosmo.contracts.pipeline.phase_contexts import DiscoveryPhaseContext
from kosmo.contracts.pipeline.phase_outputs import DiscoveryPhaseOutput
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.pipeline.skill_registry import SkillRegistry
from kosmo.domain.pipeline.tool_registry import ToolRegistry
from kosmo.infrastructure.persistence.memory.in_memory_store import (
    InMemoryAgentSessionStore,
)
from tests.factories import a_project_id
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
async def test_agent_saves_session_on_successful_completion() -> None:
    # Arrange
    llm = StubStructuredLLMClient(responses=[make_discovery_document(DISCOVERY_VALID)])
    store = InMemoryAgentSessionStore()
    agent = _make_agent(llm, memory=store)
    project_id = a_project_id()

    # Act
    result = await agent.execute_with_skill(
        skill_name="discovery_generate",
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
async def test_agent_with_memory_but_no_project_id_does_not_save() -> None:
    # Arrange
    llm = StubStructuredLLMClient(responses=[make_discovery_document(DISCOVERY_VALID)])
    store = InMemoryAgentSessionStore()
    agent = _make_agent(llm, memory=store)

    # Act
    result = await agent.execute_with_skill(
        skill_name="discovery_generate",
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
    llm = StubStructuredLLMClient(responses=[make_discovery_document(DISCOVERY_VALID)])
    store = InMemoryAgentSessionStore()
    agent = _make_agent(llm, memory=store)
    project_id = a_project_id()

    # Act
    result = await agent.execute_with_skill(
        skill_name="discovery_generate",
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
    llm = StubStructuredLLMClient(
        responses=[
            make_discovery_document(DISCOVERY_VALID),
            make_discovery_document(DISCOVERY_VALID),
        ]
    )
    store = InMemoryAgentSessionStore()
    agent = _make_agent(llm, memory=store)

    # Act
    await agent.execute_with_skill(
        skill_name="discovery_generate",
        context=DiscoveryPhaseContext(project_name="A", project_description="A"),
        project_id=project_a,
    )
    await agent.execute_with_skill(
        skill_name="discovery_generate",
        context=DiscoveryPhaseContext(project_name="B", project_description="B"),
        project_id=project_b,
    )

    # Assert
    sessions_a = await store.list_sessions(project_a)
    sessions_b = await store.list_sessions(project_b)
    assert len(sessions_a) == 1
    assert len(sessions_b) == 1
    assert sessions_a[0].project_id != sessions_b[0].project_id
