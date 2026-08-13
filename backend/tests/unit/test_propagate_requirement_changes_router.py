from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from kosmo.application.consistency.propagate_changes import PropagateChangesUseCase
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from kosmo.infrastructure.api.routers.requirements import (
    PropagateRequirementsRequest,
    propagate_requirement_changes,
)
from kosmo.infrastructure.api.schemas import PhaseNotificationList
from tests.unit.fakes import (
    FakeConsistencyEvaluator,
    InMemoryActivityDiagramRepository,
    InMemoryChatRepository,
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
)


def _make_request(uc: PropagateChangesUseCase) -> MagicMock:
    mock_req = MagicMock()
    mock_req.app.state.container = SimpleNamespace(
        consistency=SimpleNamespace(propagate_requirement_changes=uc),
    )
    return mock_req


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_requirement_changes_router_returns_affected_phases() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    feature_repo = InMemoryFeatureRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()

    project_id = ProjectId("prj_test")
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

    uc = PropagateChangesUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=diagram_repo,  # type: ignore[arg-type]
        diagram_repo=diagram_repo,
        chat_repo=chat_repo,
        consistency_evaluator=evaluator,
    )

    body = PropagateRequirementsRequest(project_id="prj_test", applied_change_ids=[])

    principal = Principal(subject="usr_test", scopes=frozenset({"*"}))

    mock_req = _make_request(uc)

    # Act
    result = await propagate_requirement_changes(
        feature_id="feat_01",
        body=body,
        _principal=principal,
        request=mock_req,
    )

    # Assert
    assert isinstance(result, PhaseNotificationList)
    phases_by_name = {p.phase: p for p in result.affected_phases}
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

    uc = PropagateChangesUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=diagram_repo,  # type: ignore[arg-type]
        diagram_repo=diagram_repo,
        chat_repo=chat_repo,
        consistency_evaluator=FakeConsistencyEvaluator(),
    )

    body = PropagateRequirementsRequest(project_id="prj_missing", applied_change_ids=[])

    principal = Principal(subject="usr_test", scopes=frozenset({"*"}))

    mock_req = _make_request(uc)

    from fastapi import HTTPException

    # Act & Assert
    with pytest.raises(HTTPException):
        await propagate_requirement_changes(
            feature_id="feat_01",
            body=body,
            _principal=principal,
            request=mock_req,
        )
