from __future__ import annotations

import pytest

from kosmo.application.consistency.propagate_requirement_changes import (
    PropagateRequirementChangesInput,
    PropagateRequirementChangesUseCase,
)
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from tests.unit.fakes import (
    FakeConsistencyEvaluator,
    InMemoryActivityDiagramRepository,
    InMemoryChatRepository,
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_requirement_changes_router_returns_affected_phases() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    feature_repo = InMemoryFeatureRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()

    project_id = ProjectId("prj_test")
    feature_id = FeatureId("feat_01")
    await project_repo.save(
        Project(
            id=project_id,
            name="Test",
            slug="test",
            description="",
            owner_id=UserId("usr_test"),
        )
    )

    evaluator = FakeConsistencyEvaluator()
    evaluator.set_affected_ids("caracteristicas", ["feat_01"])
    evaluator.set_affected_ids("descubrimiento", ["prj_test"])

    uc = PropagateRequirementChangesUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        diagram_repo=diagram_repo,
        chat_repo=chat_repo,
        consistency_evaluator=evaluator,
    )

    input_data = PropagateRequirementChangesInput(
        project_id=project_id,
        feature_id=feature_id,
        applied_change_ids=[],
    )

    # Act
    output = await uc.execute(input_data)

    # Assert
    assert isinstance(output.affected_phases, list)
    phases_by_name = {p.phase: p for p in output.affected_phases}
    assert "features" in phases_by_name
    assert "discovery" in phases_by_name
    assert phases_by_name["features"].affected_count == 1
    assert phases_by_name["discovery"].affected_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_requirement_changes_raises_on_project_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    feature_repo = InMemoryFeatureRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()

    uc = PropagateRequirementChangesUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        diagram_repo=diagram_repo,
        chat_repo=chat_repo,
        consistency_evaluator=FakeConsistencyEvaluator(),
    )

    # Act & Assert
    from kosmo.contracts.sdd.errors import ProjectNotFoundError

    with pytest.raises(ProjectNotFoundError):
        await uc.execute(
            PropagateRequirementChangesInput(
                project_id=ProjectId("prj_missing"),
                feature_id=FeatureId("feat_01"),
                applied_change_ids=[],
            )
        )
