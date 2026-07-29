import pytest

from kosmo.application.chat.manage_plan_changes import (
    ManagePlanChangesUseCase,
    PlanStateOutput,
)
from kosmo.contracts import (
    DiffCambio,
    EstadoPlanCambio,
    PlanChangeId,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import (
    PlanChangeNotFoundError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from tests.unit.fakes import (
    InMemoryChatRepository,
    InMemoryProjectRepository,
)


def _make_project(project_id: str = "prj_test") -> Project:
    return Project(
        id=ProjectId(project_id),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_test"),
    )


def _make_uc(project_repo, chat_repo):
    return ManagePlanChangesUseCase(
        project_repo=project_repo,
        chat_repo=chat_repo,
    )


# ── get_plan_state ──


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_plan_state_empty() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    uc = _make_uc(project_repo, chat_repo)

    # Act
    result = await uc.get_plan_state(project.id, SpecPhase.DESCUBRIMIENTO)

    # Assert
    assert isinstance(result, PlanStateOutput)
    assert result.pending_count == 0
    assert result.conflict_count == 0
    assert result.changes == []


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_plan_state_counts_mixed_statuses() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    uc = _make_uc(project_repo, chat_repo)

    # seed: one ADDED, one PENDING, one CONFLICT, one DISCARDED
    from kosmo.contracts import PlanCambio

    def _pc(cid: str, status: EstadoPlanCambio) -> PlanCambio:
        return PlanCambio(
            id=PlanChangeId(cid),
            section="S1",
            description="d",
            diff=DiffCambio(before="x", after="y"),
            status=status,
        )

    await chat_repo.add_plan_change(project.id, SpecPhase.DESCUBRIMIENTO, _pc("chg_a", EstadoPlanCambio.ADDED))
    await chat_repo.add_plan_change(project.id, SpecPhase.DESCUBRIMIENTO, _pc("chg_b", EstadoPlanCambio.PENDING))
    await chat_repo.add_plan_change(project.id, SpecPhase.DESCUBRIMIENTO, _pc("chg_c", EstadoPlanCambio.CONFLICT))
    await chat_repo.add_plan_change(project.id, SpecPhase.DESCUBRIMIENTO, _pc("chg_d", EstadoPlanCambio.DISCARDED))

    # Act
    result = await uc.get_plan_state(project.id, SpecPhase.DESCUBRIMIENTO)

    # Assert
    assert result.pending_count == 2
    assert result.conflict_count == 1
    assert len(result.changes) == 4


# ── add_change ──


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_change_success() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    uc = _make_uc(project_repo, chat_repo)

    # Act
    result = await uc.add_change(
        project_id=project.id,
        phase=SpecPhase.DESCUBRIMIENTO,
        change_id="chg_01",
        section="Alcance",
        description="Ampliar alcance",
        diff_before="antes",
        diff_after="después",
    )

    # Assert
    assert result.pending_count == 1
    assert result.conflict_count == 0
    assert len(result.changes) == 1
    assert result.changes[0].id == PlanChangeId("chg_01")
    assert result.changes[0].status == EstadoPlanCambio.ADDED
    assert result.changes[0].origin == "chat"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_change_idempotent() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    uc = _make_uc(project_repo, chat_repo)

    args = {
        "project_id": project.id,
        "phase": SpecPhase.DESCUBRIMIENTO,
        "change_id": "chg_01",
        "section": "Alcance",
        "description": "Ampliar alcance",
        "diff_before": "antes",
        "diff_after": "después",
    }

    # Act
    await uc.add_change(**args)
    result = await uc.add_change(**args)

    # Assert
    assert result.pending_count == 1
    assert len(result.changes) == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_change_raises_when_project_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    chat_repo = InMemoryChatRepository()
    uc = _make_uc(project_repo, chat_repo)

    # Act & Assert
    with pytest.raises(ProjectNotFoundError):
        await uc.add_change(
            project_id=ProjectId("prj_missing"),
            phase=SpecPhase.DESCUBRIMIENTO,
            change_id="chg_01",
            section="Alcance",
            description="Ampliar alcance",
            diff_before="antes",
            diff_after="después",
        )


# ── remove_change ──


@pytest.mark.asyncio
@pytest.mark.unit
async def test_remove_change_success() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    uc = _make_uc(project_repo, chat_repo)
    await uc.add_change(
        project_id=project.id,
        phase=SpecPhase.DESCUBRIMIENTO,
        change_id="chg_01",
        section="Alcance",
        description="Ampliar alcance",
        diff_before="antes",
        diff_after="después",
    )

    # Act
    result = await uc.remove_change(
        project_id=project.id,
        change_id=PlanChangeId("chg_01"),
        phase=SpecPhase.DESCUBRIMIENTO,
    )

    # Assert
    assert result.pending_count == 0
    assert len(result.changes) == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_remove_change_raises_when_not_found() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    uc = _make_uc(project_repo, chat_repo)

    # Act & Assert
    with pytest.raises(PlanChangeNotFoundError):
        await uc.remove_change(project.id, PlanChangeId("chg_missing"), SpecPhase.DESCUBRIMIENTO)


# ── accept / discard change ──


@pytest.mark.parametrize(
    "operation,expected_status",
    [
        ("accept", EstadoPlanCambio.APPLIED),
        ("discard", EstadoPlanCambio.DISCARDED),
    ],
)
@pytest.mark.asyncio
@pytest.mark.unit
async def test_accept_and_discard_change(operation: str, expected_status: EstadoPlanCambio) -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    uc = _make_uc(project_repo, chat_repo)
    await uc.add_change(
        project_id=project.id,
        phase=SpecPhase.DESCUBRIMIENTO,
        change_id="chg_01",
        section="Alcance",
        description="Ampliar alcance",
        diff_before="antes",
        diff_after="después",
    )

    # Act
    if operation == "accept":
        result = await uc.accept_change(project.id, PlanChangeId("chg_01"), SpecPhase.DESCUBRIMIENTO)
    else:
        result = await uc.discard_change(project.id, PlanChangeId("chg_01"), SpecPhase.DESCUBRIMIENTO)

    # Assert
    assert result.changes[0].status == expected_status
    assert result.pending_count == 0


# ── discard_plan ──


@pytest.mark.asyncio
@pytest.mark.unit
async def test_discard_plan_clears_all() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    uc = _make_uc(project_repo, chat_repo)
    await uc.add_change(
        project_id=project.id,
        phase=SpecPhase.DESCUBRIMIENTO,
        change_id="chg_01",
        section="Alcance",
        description="Ampliar alcance",
        diff_before="antes",
        diff_after="después",
    )
    await uc.add_change(
        project_id=project.id,
        phase=SpecPhase.DESCUBRIMIENTO,
        change_id="chg_02",
        section="Visión",
        description="Refinar visión",
        diff_before="antes",
        diff_after="después",
    )

    # Act
    await uc.discard_plan(project.id, SpecPhase.DESCUBRIMIENTO)

    # Assert
    result = await uc.get_plan_state(project.id, SpecPhase.DESCUBRIMIENTO)
    assert result.pending_count == 0
    assert len(result.changes) == 0
