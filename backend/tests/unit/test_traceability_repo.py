from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.infrastructure.persistence.postgres.models import TraceabilityEdgeModel
from kosmo.infrastructure.persistence.postgres.repositories.traceability_repo import (
    SqlAlchemyTraceabilityRepository,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_by_entity_id_executes_bulk_delete_and_commits() -> None:
    # Arrange
    mock_session = MagicMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.delete = AsyncMock()

    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyTraceabilityRepository(session_factory=mock_session_factory)

    # Act
    await repo.delete_by_entity_id("feat_123")

    # Assert: solo 1 execute con delete bulk, y NUNCA session.delete fila por fila (cero N+1)
    mock_session.execute.assert_awaited_once()
    mock_session.delete.assert_not_called()
    mock_session.commit.assert_awaited_once()

    stmt = mock_session.execute.call_args[0][0]
    assert stmt.is_delete
    assert stmt.table.name == TraceabilityEdgeModel.__tablename__


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_by_entity_id_with_direct_session_does_not_commit() -> None:
    # Arrange: en contexto UoW donde la sesion se pasa externamente
    mock_session = MagicMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    repo = SqlAlchemyTraceabilityRepository(session=mock_session)

    # Act
    await repo.delete_by_entity_id("req_456")

    # Assert
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_not_called()
