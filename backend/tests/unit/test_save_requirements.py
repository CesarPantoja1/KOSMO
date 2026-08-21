from typing import Any

import pytest

from kosmo.application.requirements.save_requirements import SaveRequirementsUseCase
from kosmo.contracts.sdd.errors import FeatureNotFoundError, ProjectNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from tests.unit.fakes import (
    InMemoryFeatureRepository,
    InMemoryOutbox,
    InMemoryProjectRepository,
    InMemoryRequirementRepository,
)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_requirements_saves_markdown() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    use_case = SaveRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
    )

    project = Project(
        id=ProjectId("prj_req01"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_01"),
    )
    await project_repo.save(project)

    feature = Feature(
        id=FeatureId("feat_req01"),
        number=1,
        title="Test Feature",
        slug="test-feature",
        description="Test feature description",
        project_id=project.id,
    )
    await feature_repo.save(feature)

    markdown = "## Requisitos EARS\n\n| ID | Categoría | Requisito |"
    project_id = ProjectId("prj_req01")
    feature_id = FeatureId("feat_req01")

    # Act
    await use_case.execute(project_id, feature_id, markdown)

    # Assert
    saved = await requirement_repo.by_feature_id(feature_id)
    assert saved is not None
    assert "Requisitos EARS" in saved


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_requirements_raises_project_not_found() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    use_case = SaveRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
    )

    project_id = ProjectId("prj_nonexistent")
    feature_id = FeatureId("feat_req02")
    markdown = "## Requisitos"

    # Act & Assert
    with pytest.raises(ProjectNotFoundError):
        await use_case.execute(project_id, feature_id, markdown)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_requirements_raises_feature_not_found() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    use_case = SaveRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
    )

    project = Project(
        id=ProjectId("prj_req03"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_03"),
    )
    await project_repo.save(project)

    project_id = ProjectId("prj_req03")
    feature_id = FeatureId("feat_nonexistent")
    markdown = "## Requisitos"

    # Act & Assert
    with pytest.raises(FeatureNotFoundError):
        await use_case.execute(project_id, feature_id, markdown)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_requirements_raises_feature_wrong_project() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    use_case = SaveRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
    )

    project_a = Project(
        id=ProjectId("prj_req04a"),
        name="Project A",
        slug="project-a",
        description="Test",
        owner_id=UserId("usr_04"),
    )
    project_b = Project(
        id=ProjectId("prj_req04b"),
        name="Project B",
        slug="project-b",
        description="Test",
        owner_id=UserId("usr_04"),
    )
    await project_repo.save(project_a)
    await project_repo.save(project_b)

    feature = Feature(
        id=FeatureId("feat_req04"),
        number=1,
        title="Feature",
        slug="feature",
        description="Feature belonging to project A",
        project_id=project_a.id,
    )
    await feature_repo.save(feature)

    project_id = ProjectId("prj_req04b")
    feature_id = FeatureId("feat_req04")
    markdown = "## Requisitos"

    # Act & Assert
    with pytest.raises(FeatureNotFoundError):
        await use_case.execute(project_id, feature_id, markdown)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_requirements_enqueues_downstream_evaluation() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    outbox = InMemoryOutbox()
    use_case = SaveRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        outbox=outbox,
    )

    project = Project(
        id=ProjectId("prj_chain"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_01"),
    )
    await project_repo.save(project)

    feature = Feature(
        id=FeatureId("feat_chain"),
        number=1,
        title="Test Feature",
        slug="test-feature",
        description="Test feature description",
        project_id=project.id,
    )
    await feature_repo.save(feature)

    markdown = "## Requisitos EARS\n\n| ID | Categoría | Requisito |"

    # Act
    await use_case.execute(project.id, feature.id, markdown)

    # Assert — editar Requisitos dispara la verificación del Modelo
    assert len(outbox.jobs) == 1
    job_type, payload = outbox.jobs[0]
    assert job_type == "consistency_evaluate"
    assert payload["project_id"] == "prj_chain"
    assert payload["source_phase"] == "requisitos"
