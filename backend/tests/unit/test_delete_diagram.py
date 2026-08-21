from __future__ import annotations

import pytest

from kosmo.application.modelo.delete_diagram import (
    DeleteActivityDiagramUseCase,
    DeleteDiagramInput,
)
from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.errors import DiagramNotFoundError, FeatureNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from tests.unit.fakes import InMemoryActivityDiagramRepository, InMemoryFeatureRepository


def _a_project(project_id: str = "prj_del_diag") -> Project:
    return Project(
        id=ProjectId(project_id),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_01"),
    )


def _a_feature(project: Project, feature_id: str = "feat_del_diag") -> Feature:
    return Feature(
        id=FeatureId(feature_id),
        number=1,
        title="Característica a limpiar",
        slug="caracteristica-a-limpiar",
        description="Descripción",
        project_id=project.id,
    )


def _a_diagram(feature: Feature) -> DiagramaActividad:
    return DiagramaActividad(
        id=ActivityDiagramId("adg_del_diag"),
        feature_id=feature.id,
        diagram_syntax="@startuml\nstart\n:accion;\nstop\n@enduml",
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_diagram_removes_activity_diagram() -> None:
    # Arrange
    project = _a_project()
    feature = _a_feature(project)

    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature)

    diagram_repo = InMemoryActivityDiagramRepository()
    await diagram_repo.save(_a_diagram(feature))

    use_case = DeleteActivityDiagramUseCase(
        feature_repo=feature_repo,
        diagram_repo=diagram_repo,
    )

    # Act
    await use_case.execute(DeleteDiagramInput(project_id=project.id, feature_id=feature.id))

    # Assert
    assert await diagram_repo.by_feature_id(feature.id) is None
    assert await diagram_repo.exists(feature.id) is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_diagram_raises_when_feature_not_found() -> None:
    # Arrange
    project = _a_project()

    use_case = DeleteActivityDiagramUseCase(
        feature_repo=InMemoryFeatureRepository(),
        diagram_repo=InMemoryActivityDiagramRepository(),
    )

    # Act & Assert
    with pytest.raises(FeatureNotFoundError) as exc_info:
        await use_case.execute(DeleteDiagramInput(project_id=project.id, feature_id=FeatureId("feat_missing")))

    assert exc_info.value.problem.status == 404
    assert "feat_missing" in exc_info.value.problem.detail


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_diagram_raises_when_diagram_not_found() -> None:
    # Arrange
    project = _a_project()
    feature = _a_feature(project)

    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature)

    use_case = DeleteActivityDiagramUseCase(
        feature_repo=feature_repo,
        diagram_repo=InMemoryActivityDiagramRepository(),
    )

    # Act & Assert
    with pytest.raises(DiagramNotFoundError) as exc_info:
        await use_case.execute(DeleteDiagramInput(project_id=project.id, feature_id=feature.id))

    assert exc_info.value.problem.status == 404
