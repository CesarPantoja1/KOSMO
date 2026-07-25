from __future__ import annotations

import pytest

from kosmo.contracts.agent_memory import AgentSessionSummary
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import AgentMemoryId, ProjectId
from kosmo.infrastructure.persistence.memory.in_memory_store import (
    InMemoryAgentSessionStore,
)
from tests.factories import a_project_id, a_session


@pytest.mark.unit
class TestInMemoryStoreSaveAndLoad:
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_save_and_load_session(self) -> None:
        # Arrange
        store = InMemoryAgentSessionStore()
        session = a_session()

        # Act
        await store.save_session(session)
        loaded = await store.load_session(session.session_id)

        # Assert
        assert loaded is not None
        assert loaded.session_id == session.session_id
        assert loaded.project_id == session.project_id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_load_nonexistent_session_returns_none(self) -> None:
        # Arrange
        store = InMemoryAgentSessionStore()

        # Act
        result = await store.load_session(AgentMemoryId("agm_nonexistent"))

        # Assert
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_save_overwrites_existing_session(self) -> None:
        # Arrange
        store = InMemoryAgentSessionStore()
        session = a_session(current_iteration=0, is_completed=False)
        await store.save_session(session)

        updated = a_session(
            session_id=session.session_id,
            project_id=session.project_id,
            session_type=session.session_type,
            phase=session.phase,
            current_iteration=5,
            is_completed=True,
        )

        # Act
        await store.save_session(updated)
        loaded = await store.load_session(session.session_id)

        # Assert
        assert loaded is not None
        assert loaded.current_iteration == 5
        assert loaded.is_completed is True


@pytest.mark.unit
class TestInMemoryStoreList:
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_sessions_by_project(self) -> None:
        # Arrange
        store = InMemoryAgentSessionStore()
        project_id = ProjectId("prj_01KT01ABC")
        s1 = a_session(project_id=project_id)
        s2 = a_session(project_id=project_id, session_type="refinement")
        s3 = a_session(project_id=ProjectId("prj_01KT01DEF"), phase=SpecPhase.REQUISITOS)
        await store.save_session(s1)
        await store.save_session(s2)
        await store.save_session(s3)

        # Act
        results = await store.list_sessions(project_id)

        # Assert
        assert len(results) == 2
        assert all(isinstance(r, AgentSessionSummary) for r in results)
        ids = {r.session_id for r in results}
        assert s1.session_id in ids
        assert s2.session_id in ids
        assert s3.session_id not in ids

    @pytest.mark.parametrize(
        "filter_phase,expected_count",
        [
            (SpecPhase.REQUISITOS, 1),
            (SpecPhase.DESCUBRIMIENTO, 1),
            (SpecPhase.CARACTERISTICAS, 0),
        ],
    )
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_sessions_filtered_by_phase(self, filter_phase: SpecPhase, expected_count: int) -> None:
        # Arrange
        store = InMemoryAgentSessionStore()
        project_id = a_project_id()
        s1 = a_session(project_id=project_id, phase=SpecPhase.DESCUBRIMIENTO)
        s2 = a_session(project_id=project_id, phase=SpecPhase.REQUISITOS)
        await store.save_session(s1)
        await store.save_session(s2)

        # Act
        results = await store.list_sessions(project_id, phase=filter_phase)

        # Assert
        assert len(results) == expected_count

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_sessions_empty_project(self) -> None:
        # Arrange
        store = InMemoryAgentSessionStore()

        # Act
        results = await store.list_sessions(ProjectId("prj_empty"))

        # Assert
        assert results == []


@pytest.mark.unit
class TestInMemoryStoreGetLatest:
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_latest_session_returns_most_recent(self) -> None:
        # Arrange
        store = InMemoryAgentSessionStore()
        project_id = a_project_id()
        s1 = a_session(project_id=project_id)
        s2 = a_session(project_id=project_id, session_type="refinement")
        await store.save_session(s1)
        await store.save_session(s2)

        # Act
        result = await store.get_latest_session(project_id, SpecPhase.DESCUBRIMIENTO)

        # Assert
        assert result is not None
        assert result.session_id == s2.session_id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_latest_session_returns_none_when_empty(self) -> None:
        # Arrange
        store = InMemoryAgentSessionStore()

        # Act
        result = await store.get_latest_session(ProjectId("prj_empty"), SpecPhase.DESCUBRIMIENTO)

        # Assert
        assert result is None


@pytest.mark.unit
class TestInMemoryStoreProjectContext:
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_project_context_aggregates_sessions(self) -> None:
        # Arrange
        store = InMemoryAgentSessionStore()
        project_id = a_project_id()
        s1 = a_session(project_id=project_id, is_completed=True)
        s2 = a_session(project_id=project_id, phase=SpecPhase.REQUISITOS, is_completed=True)
        await store.save_session(s1)
        await store.save_session(s2)

        # Act
        context = await store.get_project_context(project_id)

        # Assert
        assert context.project_id == project_id
        assert context.total_sessions == 2
        assert len(context.latest_sessions) == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_project_context_empty_project(self) -> None:
        # Arrange
        store = InMemoryAgentSessionStore()

        # Act
        context = await store.get_project_context(ProjectId("prj_empty"))

        # Assert
        assert context.project_id == ProjectId("prj_empty")
        assert context.total_sessions == 0
        assert context.latest_sessions == {}
