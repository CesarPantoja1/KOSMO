from __future__ import annotations

import pytest

from kosmo.application.consistency.propagate_feature_changes import (
    PropagateFeatureChangesInput,
    PropagateFeatureChangesUseCase,
)
from kosmo.contracts import ChatRepository, DiffCambio, EstadoPlanCambio, PlanCambio
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import PlanChangeId, ProjectId, UserId
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


def _plan_change(
    cid: str, before: str = "old", after: str = "new", status: EstadoPlanCambio = EstadoPlanCambio.APPLIED
) -> PlanCambio:
    return PlanCambio(
        id=PlanChangeId(cid),
        section="Descripción",
        description="Cambio en característica",
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
) -> PropagateFeatureChangesUseCase:
    return PropagateFeatureChangesUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=diagram_repo,
        chat_repo=chat_repo,
        consistency_evaluator=evaluator,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_propaga_cambio_caracteristica_tridireccional_exito() -> None:
    # Arrange
    project = _make_project("prj_001")
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()

    c1 = _plan_change("chg_01")
    await chat_repo.add_plan_change(project.id, SpecPhase.CARACTERISTICAS, c1)

    evaluator = FakeConsistencyEvaluator()
    # Mock responses for 3 directions: discovery (upstream), requirements (downstream), model (downstream)
    evaluator.set_affected_ids("descubrimiento", ["dsc_01"])
    evaluator.set_affected_ids("requisitos", ["req_01", "req_02"])
    evaluator.set_affected_ids("modelo", ["mdl_01"])

    uc = _make_uc(project_repo, feature_repo, requirement_repo, diagram_repo, chat_repo, evaluator)

    # Act
    out = await uc.execute(
        PropagateFeatureChangesInput(
            project_id=project.id,
            phase=SpecPhase.CARACTERISTICAS,
            applied_change_ids=[PlanChangeId("chg_01")],
        )
    )

    # Assert
    phases = {p.phase: p for p in out.affected_phases}
    assert "discovery" in phases
    assert phases["discovery"].affected_count == 1
    assert phases["discovery"].affected_ids == ["dsc_01"]

    assert "requirements" in phases
    assert phases["requirements"].affected_count == 2
    assert phases["requirements"].affected_ids == ["req_01", "req_02"]

    assert "model" in phases
    assert phases["model"].affected_count == 1
    assert phases["model"].affected_ids == ["mdl_01"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_propaga_cambio_caracteristica_proyecto_no_encontrado() -> None:
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
            PropagateFeatureChangesInput(
                project_id=ProjectId("non_existent"),
                phase=SpecPhase.CARACTERISTICAS,
                applied_change_ids=[PlanChangeId("chg_01")],
            )
        )
