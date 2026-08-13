from __future__ import annotations

import pytest

from kosmo.application.consistency.propagate_changes import (
    PropagateChangesInput,
    PropagateChangesUseCase,
)
from kosmo.contracts import ChatRepository, DiffCambio, EstadoPlanCambio, PlanCambio
from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import (
    ActivityDiagramId,
    FeatureId,
    PlanChangeId,
    ProjectId,
    UserId,
)
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
    return PropagateChangesUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=diagram_repo,
        chat_repo=chat_repo,
        consistency_evaluator=evaluator or FakeConsistencyEvaluator(),
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_feature_reports_downstream_directions_only() -> None:
    # Arrange
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
    await diagram_repo.save(
        DiagramaActividad(
            id=ActivityDiagramId("diag_01"),
            feature_id=FeatureId("feat_01"),
            diagram_syntax="@startuml\n@enduml",
        )
    )

    change = PlanCambio(
        id=PlanChangeId("chg_01"),
        section="Titulo",
        description="Cambio de alcance",
        diff=DiffCambio(before="Antes", after="Despues"),
        status=EstadoPlanCambio.APPLIED,
        context_id="feat_01",
    )
    await chat_repo.add_plan_change(project.id, SpecPhase.CARACTERISTICAS, change)

    evaluator = FakeConsistencyEvaluator()
    evaluator.set_affected_ids("descubrimiento", ["prj_test"])
    evaluator.set_affected_ids("requisitos", ["feat_01"])
    evaluator.set_affected_ids("modelo", ["feat_01"])
    uc = _make_uc(project_repo, feature_repo, requirement_repo, diagram_repo, chat_repo, evaluator)

    # Act
    result = await uc.execute(
        PropagateChangesInput(
            project_id=project.id,
            source_phase=SpecPhase.CARACTERISTICAS,
            applied_change_ids=[PlanChangeId("chg_01")],
            feature_id=FeatureId("feat_01"),
        )
    )

    # Assert: trazabilidad solo hacia la derecha, nunca hacia descubrimiento
    phases_by_name = {p.phase: p for p in result.affected_phases}
    assert len(result.affected_phases) == 2
    assert "discovery" not in phases_by_name
    assert "requirements" in phases_by_name
    assert "model" in phases_by_name


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_feature_never_evaluates_upstream() -> None:
    # Arrange
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
        PropagateChangesInput(
            project_id=project.id,
            source_phase=SpecPhase.CARACTERISTICAS,
            applied_change_ids=[],
            feature_id=FeatureId("feat_01"),
        )
    )

    # Assert: el descubrimiento no se evalúa al modificar características
    assert len(result.affected_phases) == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_feature_downstream_only_when_upstream_no_impact() -> None:
    # Arrange
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

    change = PlanCambio(
        id=PlanChangeId("chg_down"),
        section="Titulo",
        description="Cambio",
        diff=DiffCambio(before="Antes", after="Despues"),
        status=EstadoPlanCambio.APPLIED,
        context_id="feat_01",
    )
    await chat_repo.add_plan_change(project.id, SpecPhase.CARACTERISTICAS, change)

    evaluator = FakeConsistencyEvaluator()
    evaluator.set_affected_ids("descubrimiento", [])
    evaluator.set_affected_ids("requisitos", ["feat_01"])
    uc = _make_uc(project_repo, feature_repo, requirement_repo, diagram_repo, chat_repo, evaluator)

    # Act
    result = await uc.execute(
        PropagateChangesInput(
            project_id=project.id,
            source_phase=SpecPhase.CARACTERISTICAS,
            applied_change_ids=[PlanChangeId("chg_down")],
            feature_id=FeatureId("feat_01"),
        )
    )

    # Assert
    assert len(result.affected_phases) == 1
    assert result.affected_phases[0].phase == "requirements"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_feature_raises_when_project_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()
    uc = _make_uc(project_repo, feature_repo, requirement_repo, diagram_repo, chat_repo)

    # Act & Assert
    with pytest.raises(ProjectNotFoundError):
        await uc.execute(
            PropagateChangesInput(
                project_id=ProjectId("prj_missing"),
                source_phase=SpecPhase.CARACTERISTICAS,
                applied_change_ids=[],
                feature_id=FeatureId("feat_01"),
            )
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_feature_graceful_when_evaluator_fails() -> None:
    # Arrange
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

    change = PlanCambio(
        id=PlanChangeId("chg_fail"),
        section="Titulo",
        description="Cambio",
        diff=DiffCambio(before="Antes", after="Despues"),
        status=EstadoPlanCambio.APPLIED,
        context_id="feat_01",
    )
    await chat_repo.add_plan_change(project.id, SpecPhase.CARACTERISTICAS, change)

    evaluator = FakeConsistencyEvaluator()
    evaluator.set_should_fail(True)
    uc = _make_uc(project_repo, feature_repo, requirement_repo, diagram_repo, chat_repo, evaluator)

    # Act
    result = await uc.execute(
        PropagateChangesInput(
            project_id=project.id,
            source_phase=SpecPhase.CARACTERISTICAS,
            applied_change_ids=[PlanChangeId("chg_fail")],
            feature_id=FeatureId("feat_01"),
        )
    )

    # Assert: graceful degradation on all paths, no affected phases
    assert len(result.affected_phases) == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_propagate_feature_returns_empty_when_no_impact() -> None:
    # Arrange
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
        PropagateChangesInput(
            project_id=project.id,
            source_phase=SpecPhase.CARACTERISTICAS,
            applied_change_ids=[],
            feature_id=FeatureId("feat_01"),
        )
    )

    # Assert
    assert len(result.affected_phases) == 0
