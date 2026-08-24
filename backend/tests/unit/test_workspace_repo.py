from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.sdd.codegen import CodeWorkspace, WorkspaceStatus
from kosmo.contracts.sdd.ids import ProjectId, WorkspaceId
from kosmo.infrastructure.persistence.postgres.models import WorkspaceModel
from kosmo.infrastructure.persistence.postgres.repositories.workspace_repo import (
    SqlAlchemyWorkspaceRepository,
)


def _make_workspace(
    project_id: str = "prj_01",
    workspace_id: str = "ws_01",
    is_locked: bool = False,
) -> CodeWorkspace:
    now = datetime.now(UTC)
    return CodeWorkspace(
        id=WorkspaceId(workspace_id),
        project_id=ProjectId(project_id),
        status=WorkspaceStatus.READY,
        workspace_dir="/workspaces/prj_01",
        current_branch="main",
        is_locked=is_locked,
        locked_at=now if is_locked else None,
        locked_by="user_01" if is_locked else None,
        created_at=now,
        updated_at=now,
    )


def _make_async_session_mock(returned_model: WorkspaceModel | None = None) -> MagicMock:
    mock_session = MagicMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = returned_model
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()
    return mock_session


@pytest.mark.unit
@pytest.mark.asyncio
async def test_init_raises_without_session_or_factory() -> None:
    # Act & Assert
    with pytest.raises(ValueError, match="Se requiere session_factory o session"):
        SqlAlchemyWorkspaceRepository(session_factory=None, session=None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_inserts_when_no_existing_workspace() -> None:
    # Arrange
    workspace = _make_workspace()
    mock_session = _make_async_session_mock(returned_model=None)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyWorkspaceRepository(session_factory=mock_session_factory)

    # Act
    result = await repo.save(workspace)

    # Assert
    assert result == workspace
    mock_session.add.assert_called_once()
    added_model = mock_session.add.call_args[0][0]
    assert added_model.id == "ws_01"
    assert added_model.project_id == "prj_01"
    assert added_model.path == "/workspaces/prj_01"
    assert added_model.current_branch == "main"
    assert added_model.is_locked is False
    mock_session.commit.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_updates_when_existing_workspace() -> None:
    # Arrange
    now = datetime.now(UTC)
    workspace = _make_workspace(is_locked=True)
    existing_model = WorkspaceModel(
        id="ws_01",
        project_id="prj_01",
        current_branch="main",
        is_locked=False,
        locked_at=None,
        locked_by=None,
        path="/workspaces/prj_01",
        created_at=now,
        updated_at=now,
    )
    mock_session = _make_async_session_mock(returned_model=existing_model)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyWorkspaceRepository(session_factory=mock_session_factory)

    # Act
    result = await repo.save(workspace)

    # Assert
    assert result == workspace
    mock_session.add.assert_not_called()
    assert existing_model.is_locked is True
    assert existing_model.locked_by == "user_01"
    mock_session.commit.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_by_project_id_returns_workspace_when_found() -> None:
    # Arrange
    now = datetime.now(UTC)
    existing_model = WorkspaceModel(
        id="ws_01",
        project_id="prj_01",
        current_branch="feature/test",
        is_locked=True,
        locked_at=now,
        locked_by="user_42",
        path="/workspaces/prj_01",
        created_at=now,
        updated_at=now,
    )
    mock_session = _make_async_session_mock(returned_model=existing_model)
    repo = SqlAlchemyWorkspaceRepository(session=mock_session)

    # Act
    result = await repo.by_project_id(ProjectId("prj_01"))
    alias_result = await repo.get_by_project_id(ProjectId("prj_01"))

    # Assert
    assert result is not None
    assert result.id == "ws_01"
    assert result.project_id == "prj_01"
    assert result.current_branch == "feature/test"
    assert result.is_locked is True
    assert result.locked_by == "user_42"
    assert result.workspace_dir == "/workspaces/prj_01"
    assert alias_result == result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_by_project_id_returns_none_when_not_found() -> None:
    # Arrange
    mock_session = _make_async_session_mock(returned_model=None)
    repo = SqlAlchemyWorkspaceRepository(session=mock_session)

    # Act
    result = await repo.by_project_id(ProjectId("prj_missing"))

    # Assert
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_by_id_returns_workspace_when_found() -> None:
    # Arrange
    now = datetime.now(UTC)
    existing_model = WorkspaceModel(
        id="ws_99",
        project_id="prj_99",
        current_branch="main",
        is_locked=False,
        locked_at=None,
        locked_by=None,
        path="/workspaces/prj_99",
        created_at=now,
        updated_at=now,
    )
    mock_session = _make_async_session_mock(returned_model=existing_model)
    repo = SqlAlchemyWorkspaceRepository(session=mock_session)

    # Act
    result = await repo.by_id(WorkspaceId("ws_99"))

    # Assert
    assert result is not None
    assert result.id == "ws_99"
    assert result.project_id == "prj_99"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_removes_workspace() -> None:
    # Arrange
    mock_session = _make_async_session_mock()
    repo = SqlAlchemyWorkspaceRepository(session=mock_session)

    # Act
    await repo.delete(ProjectId("prj_01"))

    # Assert
    mock_session.execute.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_lock_and_release_lock() -> None:
    # Arrange
    now = datetime.now(UTC)
    existing_model = WorkspaceModel(
        id="ws_01",
        project_id="prj_01",
        current_branch="main",
        is_locked=False,
        locked_at=None,
        locked_by=None,
        path="/workspaces/prj_01",
        created_at=now,
        updated_at=now,
    )
    mock_session = _make_async_session_mock(returned_model=existing_model)
    repo = SqlAlchemyWorkspaceRepository(session=mock_session)

    # Act 1: Acquire lock — el RETURNING del UPDATE condicional devuelve la fila actualizada
    locked_model = WorkspaceModel(
        id="ws_01",
        project_id="prj_01",
        current_branch="main",
        is_locked=True,
        locked_at=now,
        locked_by="user_77",
        path="/workspaces/prj_01",
        created_at=now,
        updated_at=now,
    )
    mock_session.execute.return_value.scalar_one_or_none.return_value = locked_model
    locked_ws = await repo.update_lock(ProjectId("prj_01"), is_locked=True, locked_by="user_77")

    # Assert 1
    assert locked_ws is not None
    assert locked_ws.is_locked is True
    assert locked_ws.locked_by == "user_77"

    # Act 2: Release lock — la liberación muta la fila en el SELECT (sin condición)
    mock_session.execute.return_value.scalar_one_or_none.return_value = existing_model
    unlocked_ws = await repo.release_lock(ProjectId("prj_01"))

    # Assert 2
    assert unlocked_ws is not None
    assert unlocked_ws.is_locked is False
    assert unlocked_ws.locked_by is None
    assert existing_model.is_locked is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_lock_usa_update_condicional_al_adquirir() -> None:
    # Arrange
    mock_session = _make_async_session_mock(returned_model=None)
    repo = SqlAlchemyWorkspaceRepository(session=mock_session)

    # Act
    await repo.update_lock(ProjectId("prj_01"), is_locked=True)

    # Assert — CAS: UPDATE con WHERE is_locked = false (no un SELECT previo)
    stmt = mock_session.execute.call_args_list[0][0][0]
    assert stmt.table.name == "workspaces"
    assert "WHERE workspaces.project_id" in str(stmt)
    assert "workspaces.is_locked = false" in str(stmt).replace("IS false", "= false").lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_lock_permite_tomar_lock_stale() -> None:
    # Arrange — un proceso murió con el lock tomado; el CAS debe permitir el takeover
    mock_session = _make_async_session_mock(returned_model=None)
    repo = SqlAlchemyWorkspaceRepository(session=mock_session)

    # Act
    await repo.update_lock(ProjectId("prj_01"), is_locked=True)

    # Assert — el WHERE incluye la condición de staleness sobre locked_at
    stmt = mock_session.execute.call_args_list[0][0][0]
    rendered = str(stmt)
    assert "workspaces.locked_at <" in rendered
    assert "workspaces.locked_at IS NULL" in rendered


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_lock_returns_none_when_cas_conflict() -> None:
    # Arrange — el UPDATE condicional no afectó filas y el INSERT compite con otra fila
    mock_session = _make_async_session_mock(returned_model=None)
    repo = SqlAlchemyWorkspaceRepository(session=mock_session)

    # Act
    result = await repo.update_lock(ProjectId("prj_01"), is_locked=True)

    # Assert — ambos statements devolvieron vacío → conflicto
    assert result is None
    assert mock_session.execute.await_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_lock_inserta_fila_bloqueada_en_primera_adquisicion() -> None:
    # Arrange — CAS sin filas (aún no existe) y luego INSERT exitoso con ON CONFLICT
    from sqlalchemy.dialects import postgresql as pg

    now = datetime.now(UTC)
    inserted_model = WorkspaceModel(
        id="ws_prj_new",
        project_id="prj_new",
        current_branch="main",
        is_locked=True,
        locked_at=now,
        locked_by=None,
        path="",
        created_at=now,
        updated_at=now,
    )
    mock_session = _make_async_session_mock(returned_model=None)
    cas_result = MagicMock()
    cas_result.scalar_one_or_none.return_value = None
    insert_result = MagicMock()
    insert_result.scalar_one_or_none.return_value = inserted_model
    mock_session.execute = AsyncMock(side_effect=[cas_result, insert_result])
    repo = SqlAlchemyWorkspaceRepository(session=mock_session)

    # Act
    result = await repo.update_lock(ProjectId("prj_new"), is_locked=True)

    # Assert — la primera adquisición crea la fila ya bloqueada
    assert result is not None
    assert result.is_locked is True
    insert_stmt = mock_session.execute.call_args_list[1][0][0]
    assert isinstance(insert_stmt, pg.Insert)
    rendered = str(insert_stmt).upper()
    assert "INSERT INTO WORKSPACES" in rendered
    assert "ON CONFLICT" in rendered
    assert "DO NOTHING" in rendered


@pytest.mark.unit
@pytest.mark.asyncio
async def test_by_id_returns_none_when_not_found() -> None:
    # Arrange
    mock_session = _make_async_session_mock(returned_model=None)
    repo = SqlAlchemyWorkspaceRepository(session=mock_session)

    # Act
    result = await repo.by_id(WorkspaceId("ws_missing"))

    # Assert
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_lock_returns_none_when_workspace_not_found() -> None:
    # Arrange
    mock_session = _make_async_session_mock(returned_model=None)
    repo = SqlAlchemyWorkspaceRepository(session=mock_session)

    # Act
    result = await repo.update_lock(ProjectId("prj_missing"), is_locked=True)

    # Assert
    assert result is None
