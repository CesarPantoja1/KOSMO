from __future__ import annotations

import pytest

from kosmo.application.requirements.delete_requirements import (
    DeleteRequirementsInput,
    DeleteRequirementsUseCase,
)
from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.errors import (
    FeatureNotFoundError,
    ProjectNotFoundError,
    RequirementsNotFoundError,
)
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from tests.unit.fakes import (
    InMemoryActivityDiagramRepository,
    InMemoryFeatureRepository,
    InMemoryOutbox,
    InMemoryProjectRepository,
    InMemoryRequirementRepository,
)


def _a_project(project_id: str = "prj_del_req") -> Project:
    return Project(
        id=ProjectId(project_id),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_01"),
    )


def _a_feature(project: Project, feature_id: str = "feat_del_req") -> Feature:
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
        id=ActivityDiagramId("adg_del_req"),
        feature_id=feature.id,
        diagram_syntax="@startuml\nstart\n:accion;\nstop\n@enduml",
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_requirements_removes_markdown_and_enqueues_downstream_evaluation() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    project = _a_project()
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    feature = _a_feature(project)
    await feature_repo.save(feature)

    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(feature.id, "REQ-1.1: El sistema shall...")

    outbox = InMemoryOutbox()
    use_case = DeleteRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=InMemoryActivityDiagramRepository(),
        outbox=outbox,
    )

    # Act
    await use_case.execute(DeleteRequirementsInput(project_id=project.id, feature_id=feature.id))

    # Assert
    assert await requirement_repo.by_feature_id(feature.id) is None
    assert len(outbox.jobs) == 1
    job_type, payload = outbox.jobs[0]
    assert job_type == "consistency_evaluate"
    assert payload["project_id"] == str(project.id)
    assert payload["source_phase"] == "requisitos"
    assert payload["changes"][0]["after"] == ""


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_requirements_cascades_diagram() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    project = _a_project("prj_del_req2")
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    feature = _a_feature(project, "feat_del_req2")
    await feature_repo.save(feature)

    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(feature.id, "REQ-1.1: El sistema shall...")
    diagram_repo = InMemoryActivityDiagramRepository()
    await diagram_repo.save(_a_diagram(feature))

    use_case = DeleteRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=diagram_repo,
    )

    # Act
    await use_case.execute(DeleteRequirementsInput(project_id=project.id, feature_id=feature.id))

    # Assert — el modelo derivado de los requisitos se elimina en cascada
    assert await requirement_repo.by_feature_id(feature.id) is None
    assert await diagram_repo.by_feature_id(feature.id) is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_requirements_cascade_tolerates_missing_diagram() -> None:
    # Arrange — hay requisitos pero nunca se generó el modelo
    project_repo = InMemoryProjectRepository()
    project = _a_project("prj_del_req3")
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    feature = _a_feature(project, "feat_del_req3")
    await feature_repo.save(feature)

    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(feature.id, "REQ-1.1: El sistema shall...")

    use_case = DeleteRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=InMemoryActivityDiagramRepository(),
    )

    # Act & Assert — el cascade no falla cuando el modelo no existe
    await use_case.execute(DeleteRequirementsInput(project_id=project.id, feature_id=feature.id))
    assert await requirement_repo.by_feature_id(feature.id) is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_requirements_raises_when_project_not_found() -> None:
    # Arrange
    use_case = DeleteRequirementsUseCase(
        project_repo=InMemoryProjectRepository(),
        feature_repo=InMemoryFeatureRepository(),
        requirement_repo=InMemoryRequirementRepository(),
        diagram_repo=InMemoryActivityDiagramRepository(),
    )

    # Act & Assert
    with pytest.raises(ProjectNotFoundError) as exc_info:
        await use_case.execute(
            DeleteRequirementsInput(
                project_id=ProjectId("prj_missing"),
                feature_id=FeatureId("feat_any"),
            )
        )

    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_requirements_raises_when_feature_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    project = _a_project()
    await project_repo.save(project)

    use_case = DeleteRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=InMemoryFeatureRepository(),
        requirement_repo=InMemoryRequirementRepository(),
        diagram_repo=InMemoryActivityDiagramRepository(),
    )

    # Act & Assert
    with pytest.raises(FeatureNotFoundError) as exc_info:
        await use_case.execute(DeleteRequirementsInput(project_id=project.id, feature_id=FeatureId("feat_missing")))

    assert exc_info.value.problem.status == 404
    assert "feat_missing" in exc_info.value.problem.detail


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_requirements_raises_when_requirements_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    project = _a_project()
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    feature = _a_feature(project)
    await feature_repo.save(feature)

    use_case = DeleteRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=InMemoryRequirementRepository(),
        diagram_repo=InMemoryActivityDiagramRepository(),
    )

    # Act & Assert
    with pytest.raises(RequirementsNotFoundError) as exc_info:
        await use_case.execute(DeleteRequirementsInput(project_id=project.id, feature_id=feature.id))

    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_requirements_without_outbox_keeps_working() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    project = _a_project("prj_del_req5")
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    feature = _a_feature(project, "feat_del_req5")
    await feature_repo.save(feature)

    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(feature.id, "REQ-1.1: El sistema shall...")

    use_case = DeleteRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=InMemoryActivityDiagramRepository(),
    )

    # Act & Assert — sin outbox el caso de uso sigue funcionando
    await use_case.execute(DeleteRequirementsInput(project_id=project.id, feature_id=feature.id))
    assert await requirement_repo.by_feature_id(feature.id) is None
