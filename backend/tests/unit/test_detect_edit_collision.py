import pytest

from kosmo.application.chat.detect_edit_collision import (
    DetectEditCollisionInput,
    DetectEditCollisionOutput,
    DetectEditCollisionUseCase,
)
from kosmo.contracts import (
    DiffCambio,
    EstadoPlanCambio,
    PlanCambio,
    PlanChangeId,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from tests.unit.fakes import (
    InMemoryChatRepository,
    InMemoryProjectRepository,
)


def _make_project(project_id: str = "prj_test") -> Project:
    return Project(
        id=ProjectId(project_id),
        name="Test",
        slug="test",
        description="Test",
        owner_id=UserId("usr_test"),
    )


def _make_uc(project_repo, chat_repo):
    return DetectEditCollisionUseCase(project_repo=project_repo, chat_repo=chat_repo)


def _plan_change(
    cid: str = "chg_01",
    section: str = "Alcance",
    status: EstadoPlanCambio = EstadoPlanCambio.ADDED,
    diff_before: str = "antes",
    diff_after: str = "despues",
) -> PlanCambio:
    return PlanCambio(
        id=PlanChangeId(cid),
        section=section,
        description="Cambio",
        diff=DiffCambio(before=diff_before, after=diff_after),
        status=status,
        origin="chat",
    )


async def _seed(chat_repo, project_id, *changes: PlanCambio) -> None:
    for c in changes:
        await chat_repo.add_plan_change(project_id, SpecPhase.DESCUBRIMIENTO, c)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_no_changes_on_section_returns_empty() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    await _seed(chat_repo, project.id, _plan_change("chg_01", section="Vision"))
    uc = _make_uc(project_repo, chat_repo)

    # Act
    result = await uc.execute(
        DetectEditCollisionInput(
            project_id=project.id,
            phase=SpecPhase.DESCUBRIMIENTO,
            section="Alcance",
            current_content="otro contenido",
        )
    )

    # Assert
    assert isinstance(result, DetectEditCollisionOutput)
    assert result.has_collision is False
    assert result.collisions == []


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fragment_still_present_no_collision() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    await _seed(chat_repo, project.id, _plan_change("chg_01", diff_before="viajes nacionales"))
    uc = _make_uc(project_repo, chat_repo)

    # Act
    result = await uc.execute(
        DetectEditCollisionInput(
            project_id=project.id,
            phase=SpecPhase.DESCUBRIMIENTO,
            section="Alcance",
            current_content="El alcance incluye viajes nacionales dentro del pais y vuelos locales.",
        )
    )

    # Assert
    assert result.has_collision is False
    assert result.collisions == []
    changes = await chat_repo.list_plan_changes(project.id, SpecPhase.DESCUBRIMIENTO)
    assert changes[0].status == EstadoPlanCambio.ADDED


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fragment_missing_marked_conflict() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    await _seed(chat_repo, project.id, _plan_change("chg_01", diff_before="viajes nacionales"))
    uc = _make_uc(project_repo, chat_repo)

    # Act
    result = await uc.execute(
        DetectEditCollisionInput(
            project_id=project.id,
            phase=SpecPhase.DESCUBRIMIENTO,
            section="Alcance",
            current_content="El alcance incluye solo vuelos internacionales.",
        )
    )

    # Assert
    assert result.has_collision is True
    assert len(result.collisions) == 1
    assert result.collisions[0].id == PlanChangeId("chg_01")
    assert result.collisions[0].status == EstadoPlanCambio.CONFLICT
    assert result.collisions[0].user_version == "El alcance incluye solo vuelos internacionales."
    changes = await chat_repo.list_plan_changes(project.id, SpecPhase.DESCUBRIMIENTO)
    assert changes[0].status == EstadoPlanCambio.CONFLICT
    assert changes[0].user_version == "El alcance incluye solo vuelos internacionales."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_mixed_section_one_collides_one_does_not() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    await _seed(
        chat_repo,
        project.id,
        _plan_change("chg_01", diff_before="viajes nacionales"),
        _plan_change("chg_02", diff_before="region LATAM"),
    )
    uc = _make_uc(project_repo, chat_repo)

    # Act
    result = await uc.execute(
        DetectEditCollisionInput(
            project_id=project.id,
            phase=SpecPhase.DESCUBRIMIENTO,
            section="Alcance",
            current_content="El alcance incluye viajes nacionales pero excluye cualquier mencion internacional.",
        )
    )

    # Assert
    assert result.has_collision is True
    assert len(result.collisions) == 1
    assert result.collisions[0].id == PlanChangeId("chg_02")
    changes = await chat_repo.list_plan_changes(project.id, SpecPhase.DESCUBRIMIENTO)
    chg_01 = next(c for c in changes if str(c.id) == "chg_01")
    chg_02 = next(c for c in changes if str(c.id) == "chg_02")
    assert chg_01.status == EstadoPlanCambio.ADDED
    assert chg_02.status == EstadoPlanCambio.CONFLICT


@pytest.mark.asyncio
@pytest.mark.unit
async def test_already_conflict_refreshes_user_version() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    await _seed(
        chat_repo,
        project.id,
        _plan_change("chg_01", status=EstadoPlanCambio.CONFLICT, diff_before="viajes nacionales"),
    )
    uc = _make_uc(project_repo, chat_repo)

    # Act
    result = await uc.execute(
        DetectEditCollisionInput(
            project_id=project.id,
            phase=SpecPhase.DESCUBRIMIENTO,
            section="Alcance",
            current_content="contenido completamente diferente",
        )
    )

    # Assert
    assert result.has_collision is True
    assert result.collisions[0].status == EstadoPlanCambio.CONFLICT
    assert result.collisions[0].user_version == "contenido completamente diferente"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_applied_and_discarded_untouched() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    await _seed(
        chat_repo,
        project.id,
        _plan_change("chg_01", status=EstadoPlanCambio.APPLIED, diff_before="viajes nacionales"),
        _plan_change("chg_02", status=EstadoPlanCambio.DISCARDED, diff_before="region LATAM"),
    )
    uc = _make_uc(project_repo, chat_repo)

    # Act
    result = await uc.execute(
        DetectEditCollisionInput(
            project_id=project.id,
            phase=SpecPhase.DESCUBRIMIENTO,
            section="Alcance",
            current_content="contenido sin ningun fragmento",
        )
    )

    # Assert
    assert result.has_collision is False
    assert result.collisions == []
    changes = await chat_repo.list_plan_changes(project.id, SpecPhase.DESCUBRIMIENTO)
    assert changes[0].status == EstadoPlanCambio.APPLIED
    assert changes[1].status == EstadoPlanCambio.DISCARDED


@pytest.mark.asyncio
@pytest.mark.unit
async def test_raises_when_project_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    chat_repo = InMemoryChatRepository()
    uc = _make_uc(project_repo, chat_repo)

    # Act & Assert
    with pytest.raises(ProjectNotFoundError):
        await uc.execute(
            DetectEditCollisionInput(
                project_id=ProjectId("prj_missing"),
                phase=SpecPhase.DESCUBRIMIENTO,
                section="Alcance",
                current_content="contenido",
            )
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_different_section_untouched() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    await _seed(
        chat_repo,
        project.id,
        _plan_change("chg_01", section="Alcance", diff_before="fragmento"),
    )
    uc = _make_uc(project_repo, chat_repo)

    # Act
    result = await uc.execute(
        DetectEditCollisionInput(
            project_id=project.id,
            phase=SpecPhase.DESCUBRIMIENTO,
            section="Vision",
            current_content="contenido sin fragmento",
        )
    )

    # Assert
    assert result.has_collision is False
    changes = await chat_repo.list_plan_changes(project.id, SpecPhase.DESCUBRIMIENTO)
    assert changes[0].status == EstadoPlanCambio.ADDED
