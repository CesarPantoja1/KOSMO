from __future__ import annotations

import pytest

from kosmo.application.consistency.propagate_changes import (
    PropagateChangesInput,
    PropagateChangesUseCase,
)
from kosmo.contracts import DiffCambio, EstadoPlanCambio, PlanCambio
from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId, PlanChangeId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from tests.unit.fakes import (
    FakeConsistencyEvaluator,
    InMemoryActivityDiagramRepository,
    InMemoryChatRepository,
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
)


@pytest.fixture
def fakes() -> dict[str, object]:
    return {
        "project_repo": InMemoryProjectRepository(),
        "feature_repo": InMemoryFeatureRepository(),
        "diagram_repo": InMemoryActivityDiagramRepository(),
        "chat_repo": InMemoryChatRepository(),
        "consistency_evaluator": FakeConsistencyEvaluator(),
    }


@pytest.fixture
def use_case(fakes: dict[str, object]) -> PropagateChangesUseCase:
    return PropagateChangesUseCase(
        project_repo=fakes["project_repo"],  # type: ignore[arg-type]
        feature_repo=fakes["feature_repo"],  # type: ignore[arg-type]
        requirement_repo=fakes["diagram_repo"],  # type: ignore[arg-type]
        diagram_repo=fakes["diagram_repo"],  # type: ignore[arg-type]
        chat_repo=fakes["chat_repo"],  # type: ignore[arg-type]
        consistency_evaluator=fakes["consistency_evaluator"],  # type: ignore[arg-type]
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_project_not_found(use_case: PropagateChangesUseCase) -> None:
    with pytest.raises(ProjectNotFoundError):
        await use_case.execute(
            PropagateChangesInput(
                project_id=ProjectId("no-existe"),
                source_phase=SpecPhase.REQUISITOS,
                applied_change_ids=[],
                feature_id=FeatureId("feat-1"),
            )
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_successful_propagation_with_impacts(
    use_case: PropagateChangesUseCase,
    fakes: dict[str, object],
) -> None:
    project_repo: InMemoryProjectRepository = fakes["project_repo"]  # type: ignore
    chat_repo: InMemoryChatRepository = fakes["chat_repo"]  # type: ignore
    diagram_repo: InMemoryActivityDiagramRepository = fakes["diagram_repo"]  # type: ignore
    evaluator: FakeConsistencyEvaluator = fakes["consistency_evaluator"]  # type: ignore

    project_id = ProjectId("proj-1")
    feature_id = FeatureId("feat-1")
    await project_repo.save(Project(id=project_id, name="Test", slug="test", owner_id=UserId("u1"), description="test"))

    await diagram_repo.save(
        DiagramaActividad(id=ActivityDiagramId("diag-1"), feature_id=feature_id, diagram_syntax="syntax")
    )

    change_id_1 = PlanChangeId("c1")
    change_id_2 = PlanChangeId("c2")
    await chat_repo.add_plan_change(
        project_id,
        SpecPhase.REQUISITOS,
        PlanCambio(
            id=change_id_1,
            context_id=str(feature_id),
            diff=DiffCambio(before="old", after="new"),
            status=EstadoPlanCambio.PENDING,
            description="desc",
            section="sec",
        ),
    )
    await chat_repo.add_plan_change(
        project_id,
        SpecPhase.REQUISITOS,
        PlanCambio(
            id=change_id_2,
            context_id=str(feature_id),
            diff=DiffCambio(before="old", after="new"),
            status=EstadoPlanCambio.PENDING,
            description="desc",
            section="sec",
        ),
    )

    evaluator.set_affected_ids("caracteristicas", ["some-id", "some-other-id"])
    evaluator.set_affected_ids("descubrimiento", ["doc-id-1", "doc-id-2"])
    evaluator.set_affected_ids("modelo", [str(feature_id)])

    output = await use_case.execute(
        PropagateChangesInput(
            project_id=project_id,
            source_phase=SpecPhase.REQUISITOS,
            applied_change_ids=[change_id_1, change_id_2],
            feature_id=feature_id,
        )
    )

    # Assert: trazabilidad solo hacia la derecha, desde requisitos solo el modelo
    assert len(output.affected_phases) == 1

    mod = next(p for p in output.affected_phases if p.phase == "model")
    assert mod.affected_count == 1
    assert mod.affected_ids == [str(feature_id)]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_model_exists(
    use_case: PropagateChangesUseCase,
    fakes: dict[str, object],
) -> None:
    project_repo: InMemoryProjectRepository = fakes["project_repo"]  # type: ignore
    evaluator: FakeConsistencyEvaluator = fakes["consistency_evaluator"]  # type: ignore

    project_id = ProjectId("proj-1")
    feature_id = FeatureId("feat-1")
    await project_repo.save(Project(id=project_id, name="Test", slug="test", owner_id=UserId("u1"), description="test"))

    evaluator.set_affected_ids("caracteristicas", [])
    evaluator.set_affected_ids("descubrimiento", [])
    evaluator.set_affected_ids("modelo", [])

    output = await use_case.execute(
        PropagateChangesInput(
            project_id=project_id,
            source_phase=SpecPhase.REQUISITOS,
            applied_change_ids=[],
            feature_id=feature_id,
        )
    )

    assert len(output.affected_phases) == 0
