from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.agent_memory.session_factory import create_session, generate_session_id


@pytest.mark.unit
@pytest.mark.property
@given(
    is_completed=st.booleans(),
    current_iteration=st.integers(min_value=0, max_value=100),
)
def test_create_session_id_always_prefixed(
    is_completed: bool,
    current_iteration: int,
) -> None:
    # Act
    result = create_session(
        project_id=ProjectId("prj_01KT01ABC"),
        session_type="generation",
        phase=SpecPhase.DESCUBRIMIENTO,
        is_completed=is_completed,
        current_iteration=current_iteration,
    )

    # Assert
    assert result.session_id.startswith("agm_")


@pytest.mark.unit
@pytest.mark.property
@given(
    is_completed=st.booleans(),
    user_instructions=st.text(min_size=1, max_size=100),
)
def test_create_session_user_instructions_roundtrip(
    is_completed: bool,
    user_instructions: str,
) -> None:
    # Act
    result = create_session(
        project_id=ProjectId("prj_01KT01ABC"),
        session_type="refinement",
        phase=SpecPhase.REQUISITOS,
        is_completed=is_completed,
        user_instructions=user_instructions,
    )

    # Assert
    assert result.user_instructions == user_instructions


@pytest.mark.unit
@pytest.mark.property
@given(
    is_completed=st.booleans(),
    max_iterations=st.integers(min_value=0, max_value=50),
)
def test_create_session_max_iterations_preserved(
    is_completed: bool,
    max_iterations: int,
) -> None:
    # Act
    result = create_session(
        project_id=ProjectId("prj_01KT01ABC"),
        session_type="generation",
        phase=SpecPhase.DESCUBRIMIENTO,
        max_iterations=max_iterations,
        is_completed=is_completed,
    )

    # Assert
    assert result.max_iterations == max_iterations


@pytest.mark.unit
@pytest.mark.property
@given(n=st.integers(min_value=1, max_value=100))
def test_generate_session_id_always_unique_across_calls(n: int) -> None:
    # Act
    ids = [generate_session_id() for _ in range(n)]

    # Assert
    assert len(ids) == len(set(ids))
    assert all(id_.startswith("agm_") for id_ in ids)
