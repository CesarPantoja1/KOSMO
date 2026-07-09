from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from kosmo.contracts.agent_memory import AgentSession
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.agent_memory.session_factory import create_session, generate_session_id
from tests.factories import a_session


@pytest.mark.unit
class TestGenerateSessionId:
    def test_generates_unique_ids(self) -> None:
        # Arrange / Act
        id1 = generate_session_id()
        id2 = generate_session_id()

        # Assert
        assert id1 != id2
        assert id1.startswith("agm_")
        assert id2.startswith("agm_")

    def test_id_has_expected_length(self) -> None:
        # Act
        result = generate_session_id()

        # Assert
        assert len(result) >= 4 + 26  # "agm_" + ULID (26 chars)


@pytest.mark.unit
class TestCreateSession:
    def test_creates_session_with_defaults(self) -> None:
        # Act
        result = create_session(
            project_id=ProjectId("prj_01KT01ABC"),
            session_type="generation",
            phase=SpecPhase.DESCUBRIMIENTO,
        )

        # Assert
        assert isinstance(result, AgentSession)
        assert result.session_id.startswith("agm_")
        assert result.project_id == ProjectId("prj_01KT01ABC")
        assert result.session_type == "generation"
        assert result.phase == SpecPhase.DESCUBRIMIENTO
        assert result.conversation == []
        assert result.reasoning_log == []
        assert result.tool_results == []
        assert result.current_iteration == 0
        assert result.max_iterations == 8
        assert result.is_completed is False

    @pytest.mark.parametrize(
        "session_type,phase,expected_type,expected_phase",
        [
            ("generation", SpecPhase.DESCUBRIMIENTO, "generation", SpecPhase.DESCUBRIMIENTO),
            ("refinement", SpecPhase.REQUISITOS, "refinement", SpecPhase.REQUISITOS),
            ("generation", SpecPhase.CARACTERISTICAS, "generation", SpecPhase.CARACTERISTICAS),
        ],
    )
    def test_creates_session_for_different_phases(
        self,
        session_type: str,
        phase: SpecPhase,
        expected_type: str,
        expected_phase: SpecPhase,
    ) -> None:
        # Act
        result = create_session(
            project_id=ProjectId("prj_01KT01ABC"),
            session_type=session_type,
            phase=phase,
        )

        # Assert
        assert result.session_type == expected_type
        assert result.phase == expected_phase

    @pytest.mark.parametrize(
        "field_name,override_value",
        [
            ("current_iteration", 5),
            ("max_iterations", 4),
            ("is_completed", True),
            ("validation_is_valid", True),
            ("total_llm_calls", 12),
            ("user_instructions", "hazlo mas conciso"),
        ],
    )
    def test_creates_session_with_field_overrides(self, field_name: str, override_value: object) -> None:
        # Act
        result = create_session(
            project_id=ProjectId("prj_01KT01ABC"),
            session_type="generation",
            phase=SpecPhase.DESCUBRIMIENTO,
            **{field_name: override_value},  # type: ignore[reportUnknownArgumentType]
        )

        # Assert
        assert getattr(result, field_name) == override_value

    def test_session_is_immutable(self) -> None:
        # Arrange
        session = a_session()

        # Act & Assert
        with pytest.raises(FrozenInstanceError):
            session.is_completed = True  # type: ignore[misc]

    def test_conversation_default_is_distinct_per_instance(self) -> None:
        # Act
        s1 = create_session(
            project_id=ProjectId("prj_01KT01ABC"),
            session_type="generation",
            phase=SpecPhase.DESCUBRIMIENTO,
        )
        s2 = create_session(
            project_id=ProjectId("prj_01KT01DEF"),
            session_type="refinement",
            phase=SpecPhase.REQUISITOS,
        )

        # Assert
        assert s1.conversation is not s2.conversation


@pytest.mark.unit
class TestSessionBuilder:
    def test_builder_provides_sensible_defaults(self) -> None:
        # Act
        result = a_session()

        # Assert
        assert isinstance(result, AgentSession)
        assert result.session_id.startswith("agm_")
        assert result.current_iteration == 0
        assert result.is_completed is False

    def test_builder_accepts_overrides(self) -> None:
        # Act
        result = a_session(
            project_id=ProjectId("prj_custom"),
            is_completed=True,
            user_instructions="refinamiento",
        )

        # Assert
        assert result.project_id == ProjectId("prj_custom")
        assert result.is_completed is True
        assert result.user_instructions == "refinamiento"

    def test_builder_generates_unique_ids_by_default(self) -> None:
        # Act
        s1 = a_session()
        s2 = a_session()

        # Assert
        assert s1.session_id != s2.session_id
