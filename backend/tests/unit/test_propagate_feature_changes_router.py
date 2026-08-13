from __future__ import annotations

import pytest

from kosmo.application.consistency.propagate_changes import (
    PropagateChangesUseCase,
)
from kosmo.contracts import DiffCambio, EstadoPlanCambio, PlanCambio
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, PlanChangeId, UserId
from kosmo.contracts.sdd.project import Project
from kosmo.infrastructure.api.routers.features import propagate_feature_changes
from kosmo.infrastructure.api.schemas import (
    PhaseNotificationList,
    PropagateFeatureChangesRequest,
)
from tests.unit.fakes import (
    FakeConsistencyEvaluator,
    InMemoryActivityDiagramRepository,
    InMemoryChatRepository,
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
    InMemoryRequirementRepository,
)


def _principal() -> Principal:
    return Principal(subject="usr_test", scopes=frozenset({"*"}))


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_feature_changes_endpoint_returns_affected_phases() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()

    project = Project(
        id="prj_test",  # type: ignore[reportArgumentType]
        name="Test",
        slug="test",
        description="",
        owner_id=UserId("usr_test"),
    )
    await project_repo.save(project)
    feature = Feature(
        id=FeatureId("feat_01"),
        project_id=project.id,
        number=1,
        title="Feature test",
        slug="feature-test",
        description="Desc.",
    )
    await feature_repo.save(feature)
    await requirement_repo.save(FeatureId("feat_01"), "# Requisitos\ntest")

    change = PlanCambio(
        id=PlanChangeId("chg_01"),
        section="Titulo",
        description="Cambio",
        diff=DiffCambio(before="Antes", after="Despues"),
        status=EstadoPlanCambio.APPLIED,
        context_id="feat_01",
    )
    await chat_repo.add_plan_change(project.id, SpecPhase.CARACTERISTICAS, change)

    evaluator = FakeConsistencyEvaluator()
    evaluator.set_affected_ids("descubrimiento", ["prj_test"])
    evaluator.set_affected_ids("requisitos", ["feat_01"])

    uc = PropagateChangesUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=diagram_repo,
        chat_repo=chat_repo,
        consistency_evaluator=evaluator,
    )

    request = PropagateFeatureChangesRequest(applied_change_ids=["chg_01"])

    # Act
    result = await propagate_feature_changes(
        project_id="prj_test",
        feature_id="feat_01",
        _principal=_principal(),
        request=request,
        uc=uc,
    )

    # Assert: trazabilidad solo hacia la derecha
    assert isinstance(result, PhaseNotificationList)
    phases_by_name = {p.phase: p for p in result.affected_phases}
    assert "discovery" not in phases_by_name
    assert "requirements" in phases_by_name
    assert phases_by_name["requirements"].affected_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_feature_changes_endpoint_raises_404_when_project_not_found() -> None:
    # Arrange
    from fastapi import HTTPException

    project_repo = InMemoryProjectRepository()
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()

    uc = PropagateChangesUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=diagram_repo,
        chat_repo=chat_repo,
        consistency_evaluator=FakeConsistencyEvaluator(),
    )

    request = PropagateFeatureChangesRequest(applied_change_ids=[])

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await propagate_feature_changes(
            project_id="prj_missing",
            feature_id="feat_01",
            _principal=_principal(),
            request=request,
            uc=uc,
        )

    assert exc_info.value.status_code == 404
