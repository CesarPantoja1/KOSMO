from __future__ import annotations

import pytest

from kosmo.application.consistency.propagate_discovery_changes import (
    PropagateDiscoveryChangesInput,
    PropagateDiscoveryChangesUseCase,
)
from kosmo.contracts import ChatRepository, DiffCambio, EstadoPlanCambio, PlanCambio
from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId, PlanChangeId, ProjectId, UserId
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


def _make_feature(feature_id: str, project_id: str, title: str, number: int = 1) -> Feature:
    return Feature(
        id=FeatureId(feature_id),
        number=number,
        title=title,
        slug=title.lower().replace(" ", "-"),
        description=f"Descripción de {title}",
        project_id=ProjectId(project_id),
        origin="Derivado de Descubrimiento",
    )


def _make_diagram(feature_id: str, diagram_id: str = "dgr_test") -> DiagramaActividad:
    return DiagramaActividad(
        id=ActivityDiagramId(diagram_id),
        feature_id=FeatureId(feature_id),
        diagram_syntax="@startuml\nA --> B\n@enduml",
    )


def _plan_change(
    cid: str, before: str = "old", after: str = "new", status: EstadoPlanCambio = EstadoPlanCambio.APPLIED
) -> PlanCambio:
    return PlanCambio(
        id=PlanChangeId(cid),
        section="Alcance",
        description="Cambio de alcance",
        diff=DiffCambio(before=before, after=after),
        status=status,
    )


def _make_uc(
    project_repo: ProjectRepository,
    feature_repo: FeatureRepository,
    requirement_repo: RequirementRepository,
    diagram_repo: ActivityDiagramRepository,
    chat_repo: ChatRepository,
    evaluator: FakeConsistencyEvaluator,
) -> PropagateDiscoveryChangesUseCase:
    return PropagateDiscoveryChangesUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=diagram_repo,
        chat_repo=chat_repo,
        consistency_evaluator=evaluator,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_propaga_features_requirements_y_modelos_afectados() -> None:
    # Arrange
    project = _make_project("prj_001")
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    feat = _make_feature("feat_01", "prj_001", "Gestión de catálogo", number=1)
    await feature_repo.save(feat)

    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(FeatureId("feat_01"), "# REQ-1.1\nEARS requirement content.")

    diagram_repo = InMemoryActivityDiagramRepository()
    await diagram_repo.save(_make_diagram("feat_01", "dgr_01"))

    chat_repo = InMemoryChatRepository()
    change = _plan_change("chg_01")
    await chat_repo.add_plan_change(ProjectId("prj_001"), SpecPhase.DESCUBRIMIENTO, change)

    evaluator = FakeConsistencyEvaluator()
    evaluator.set_affected_ids("caracteristicas", ["feat_01"])
    evaluator.set_affected_ids("requisitos", ["feat_01"])
    evaluator.set_affected_ids("modelo", ["feat_01"])

    uc = _make_uc(project_repo, feature_repo, requirement_repo, diagram_repo, chat_repo, evaluator)

    # Act
    result = await uc.execute(
        PropagateDiscoveryChangesInput(
            project_id=ProjectId("prj_001"),
            phase=SpecPhase.DESCUBRIMIENTO,
            applied_change_ids=[PlanChangeId("chg_01")],
        )
    )

    # Assert
    assert len(result.affected_phases) == 3
    phases_by_name = {p.phase: p for p in result.affected_phases}
    assert "features" in phases_by_name
    assert phases_by_name["features"].affected_count == 1
    assert phases_by_name["features"].affected_ids == ["feat_01"]
    assert "requirements" in phases_by_name
    assert phases_by_name["requirements"].affected_ids == ["feat_01"]
    assert "model" in phases_by_name
    assert phases_by_name["model"].affected_ids == ["feat_01"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_proyecto_no_encontrado_lanza_error() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()
    evaluator = FakeConsistencyEvaluator()
    uc = _make_uc(project_repo, feature_repo, requirement_repo, diagram_repo, chat_repo, evaluator)

    # Act & Assert
    with pytest.raises(ProjectNotFoundError):
        await uc.execute(
            PropagateDiscoveryChangesInput(
                project_id=ProjectId("prj_nonexistent"),
                phase=SpecPhase.DESCUBRIMIENTO,
                applied_change_ids=[],
            )
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sin_artefactos_downstream_retorna_lista_vacia() -> None:
    # Arrange
    project = _make_project("prj_002")
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()
    evaluator = FakeConsistencyEvaluator()
    uc = _make_uc(project_repo, feature_repo, requirement_repo, diagram_repo, chat_repo, evaluator)

    # Act
    result = await uc.execute(
        PropagateDiscoveryChangesInput(
            project_id=ProjectId("prj_002"),
            phase=SpecPhase.DESCUBRIMIENTO,
            applied_change_ids=[],
        )
    )

    # Assert
    assert len(result.affected_phases) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluator_falla_retorna_sin_afectados_fail_open() -> None:
    # Arrange
    project = _make_project("prj_003")
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    feat1 = _make_feature("feat_11", "prj_003", "Feature A", number=1)
    feat2 = _make_feature("feat_12", "prj_003", "Feature B", number=2)
    await feature_repo.save(feat1)
    await feature_repo.save(feat2)

    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(FeatureId("feat_11"), "# REQ Markdown")

    diagram_repo = InMemoryActivityDiagramRepository()
    await diagram_repo.save(_make_diagram("feat_11", "dgr_11"))

    chat_repo = InMemoryChatRepository()
    change = _plan_change("chg_fail")
    await chat_repo.add_plan_change(ProjectId("prj_003"), SpecPhase.DESCUBRIMIENTO, change)

    evaluator = FakeConsistencyEvaluator()
    evaluator.set_should_fail(True)

    uc = _make_uc(project_repo, feature_repo, requirement_repo, diagram_repo, chat_repo, evaluator)

    # Act
    result = await uc.execute(
        PropagateDiscoveryChangesInput(
            project_id=ProjectId("prj_003"),
            phase=SpecPhase.DESCUBRIMIENTO,
            applied_change_ids=[PlanChangeId("chg_fail")],
        )
    )

    # Assert: evaluator falla → fail-open, sin artefactos afectados
    assert len(result.affected_phases) == 0
