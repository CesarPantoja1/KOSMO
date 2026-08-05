from __future__ import annotations

import pytest

from kosmo.contracts import ChatRepository
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)
from tests.unit.fakes import (
    FakeConsistencyEvaluator,
    InMemoryActivityDiagramRepository,
    InMemoryChatRepository,
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
    InMemoryRequirementRepository,
)


def _make_project(project_id: str = "prj_test") -> Project:
    return Project(
        id=ProjectId(project_id),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_test"),
    )


def _make_uc(
    project_repo: ProjectRepository,
    feature_repo: FeatureRepository,
    requirement_repo: RequirementRepository,
    diagram_repo: ActivityDiagramRepository,
    chat_repo: ChatRepository,
    evaluator: FakeConsistencyEvaluator | None = None,
):
    from kosmo.application.consistency.propagate_feature_changes import (
        PropagateFeatureChangesUseCase,
    )

    return PropagateFeatureChangesUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=diagram_repo,
        chat_repo=chat_repo,
        consistency_evaluator=evaluator or FakeConsistencyEvaluator(),
    )


# ── happy path ──


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_feature_reports_all_three_directions() -> None:
    # Arrange
    from kosmo.application.consistency.propagate_feature_changes import (
        PropagateFeatureChangesInput,
    )

    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()

    feature = Feature(
        id=FeatureId("feat_01"),
        project_id=project.id,
        number=1,
        title="Feature test",
        slug="feature-test",
        description="Descripcion.",
    )
    await feature_repo.save(feature)
    await requirement_repo.save(FeatureId("feat_01"), "# Requisitos\ntest")
    from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
    from kosmo.contracts.sdd.ids import ActivityDiagramId

    await diagram_repo.save(
        DiagramaActividad(
            id=ActivityDiagramId("diag_01"),
            feature_id=FeatureId("feat_01"),
            diagram_syntax="@startuml\n@enduml",
        )
    )

    evaluator = FakeConsistencyEvaluator()
    evaluator.set_affected_ids("descubrimiento", ["prj_test"])
    uc = _make_uc(project_repo, feature_repo, requirement_repo, diagram_repo, chat_repo, evaluator)

    # Act
    result = await uc.execute(
        PropagateFeatureChangesInput(
            project_id=project.id,
            feature_id=FeatureId("feat_01"),
            applied_change_ids=[],
        )
    )

    # Assert
    phases_by_name = {p.phase: p for p in result.affected_phases}
    assert len(result.affected_phases) == 3
    assert "discovery" in phases_by_name
    assert "requirements" in phases_by_name
    assert "model" in phases_by_name
    assert phases_by_name["requirements"].affected_count == 1
    assert phases_by_name["model"].affected_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_feature_upstream_only_when_no_requirements_or_diagrams() -> None:
    # Arrange
    from kosmo.application.consistency.propagate_feature_changes import (
        PropagateFeatureChangesInput,
    )

    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()

    feature = Feature(
        id=FeatureId("feat_01"),
        project_id=project.id,
        number=1,
        title="Feature test",
        slug="feature-test",
        description="Descripcion.",
    )
    await feature_repo.save(feature)

    evaluator = FakeConsistencyEvaluator()
    evaluator.set_affected_ids("descubrimiento", ["prj_test"])
    uc = _make_uc(project_repo, feature_repo, requirement_repo, diagram_repo, chat_repo, evaluator)

    # Act
    result = await uc.execute(
        PropagateFeatureChangesInput(
            project_id=project.id,
            feature_id=FeatureId("feat_01"),
            applied_change_ids=[],
        )
    )

    # Assert
    assert len(result.affected_phases) == 1
    assert result.affected_phases[0].phase == "discovery"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_feature_downstream_only_when_upstream_no_impact() -> None:
    # Arrange
    from kosmo.application.consistency.propagate_feature_changes import (
        PropagateFeatureChangesInput,
    )

    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()

    feature = Feature(
        id=FeatureId("feat_01"),
        project_id=project.id,
        number=1,
        title="Feature test",
        slug="feature-test",
        description="Descripcion.",
    )
    await feature_repo.save(feature)
    await requirement_repo.save(FeatureId("feat_01"), "# Requisitos\ntest")

    evaluator = FakeConsistencyEvaluator()
    evaluator.set_affected_ids("descubrimiento", [])
    uc = _make_uc(project_repo, feature_repo, requirement_repo, diagram_repo, chat_repo, evaluator)

    # Act
    result = await uc.execute(
        PropagateFeatureChangesInput(
            project_id=project.id,
            feature_id=FeatureId("feat_01"),
            applied_change_ids=[],
        )
    )

    # Assert
    assert len(result.affected_phases) == 1
    assert result.affected_phases[0].phase == "requirements"


# ── error paths ──


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_feature_raises_when_project_not_found() -> None:
    # Arrange
    from kosmo.application.consistency.propagate_feature_changes import (
        PropagateFeatureChangesInput,
    )

    project_repo = InMemoryProjectRepository()
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()
    uc = _make_uc(project_repo, feature_repo, requirement_repo, diagram_repo, chat_repo)

    # Act & Assert
    with pytest.raises(ProjectNotFoundError):
        await uc.execute(
            PropagateFeatureChangesInput(
                project_id=ProjectId("prj_missing"),
                feature_id=FeatureId("feat_01"),
                applied_change_ids=[],
            )
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_feature_graceful_when_evaluator_fails() -> None:
    # Arrange
    from kosmo.application.consistency.propagate_feature_changes import (
        PropagateFeatureChangesInput,
    )

    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()

    feature = Feature(
        id=FeatureId("feat_01"),
        project_id=project.id,
        number=1,
        title="Feature test",
        slug="feature-test",
        description="Descripcion.",
    )
    await feature_repo.save(feature)
    await requirement_repo.save(FeatureId("feat_01"), "# Requisitos\ntest")

    evaluator = FakeConsistencyEvaluator()
    evaluator.set_should_fail(True)
    uc = _make_uc(project_repo, feature_repo, requirement_repo, diagram_repo, chat_repo, evaluator)

    # Act
    result = await uc.execute(
        PropagateFeatureChangesInput(
            project_id=project.id,
            feature_id=FeatureId("feat_01"),
            applied_change_ids=[],
        )
    )

    # Assert: graceful degradation, downstream still reported
    assert len(result.affected_phases) == 1
    assert result.affected_phases[0].phase == "requirements"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_feature_returns_empty_when_no_impact() -> None:
    # Arrange
    from kosmo.application.consistency.propagate_feature_changes import (
        PropagateFeatureChangesInput,
    )

    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()

    feature = Feature(
        id=FeatureId("feat_01"),
        project_id=project.id,
        number=1,
        title="Feature test",
        slug="feature-test",
        description="Descripcion.",
    )
    await feature_repo.save(feature)

    evaluator = FakeConsistencyEvaluator()
    evaluator.set_affected_ids("descubrimiento", [])
    uc = _make_uc(project_repo, feature_repo, requirement_repo, diagram_repo, chat_repo, evaluator)

    # Act
    result = await uc.execute(
        PropagateFeatureChangesInput(
            project_id=project.id,
            feature_id=FeatureId("feat_01"),
            applied_change_ids=[],
        )
    )

    # Assert
    assert len(result.affected_phases) == 0
