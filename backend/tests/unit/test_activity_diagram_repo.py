from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId
from kosmo.infrastructure.persistence.postgres.models import ActivityDiagramModel
from kosmo.infrastructure.persistence.postgres.repositories.activity_diagram_repo import (
    SqlAlchemyActivityDiagramRepository,
)


def _make_diagram(feature_id: str = "feat_01") -> DiagramaActividad:
    now = datetime.now(UTC)
    return DiagramaActividad(
        id=ActivityDiagramId("dia_01"),
        feature_id=FeatureId(feature_id),
        diagram_syntax="@startuml\nstart\nstop\n@enduml",
        created_at=now,
        updated_at=now,
    )


def _make_async_session_mock(returned_model: ActivityDiagramModel | None = None) -> MagicMock:
    mock_session = MagicMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = returned_model
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()
    return mock_session


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_inserts_when_no_existing_diagram() -> None:
    # Arrange
    diagram = _make_diagram()
    mock_session = _make_async_session_mock(returned_model=None)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyActivityDiagramRepository(session_factory=mock_session_factory)

    # Act
    result = await repo.save(diagram)

    # Assert
    assert result is diagram
    mock_session.add.assert_called_once()
    added_model = mock_session.add.call_args[0][0]  # type: ignore[union-attr]
    assert added_model.feature_id == "feat_01"
    assert added_model.diagram_syntax == "@startuml\nstart\nstop\n@enduml"
    mock_session.commit.assert_awaited_once()  # type: ignore[no-untyped-call]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_updates_when_diagram_exists_for_feature() -> None:
    # Arrange
    first = _make_diagram(feature_id="feat_01")
    second = DiagramaActividad(
        id=ActivityDiagramId("dia_02"),
        feature_id=FeatureId("feat_01"),
        diagram_syntax="@startuml\nstart\n:New;\nstop\n@enduml",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    existing_model = ActivityDiagramModel(
        id="dia_01",
        feature_id="feat_01",
        diagram_syntax="@startuml\nstart\nstop\n@enduml",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    mock_session = _make_async_session_mock(returned_model=existing_model)
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = SqlAlchemyActivityDiagramRepository(session_factory=mock_session_factory)

    # Save first diagram
    await repo.save(first)

    # Reset mock to respond with existing_model for the second save too
    mock_session = _make_async_session_mock(returned_model=existing_model)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    # Act: save second diagram with same feature_id but different diagram id
    result = await repo.save(second)

    # Assert
    assert result is second
    mock_session.add.assert_not_called()
    assert existing_model.diagram_syntax == "@startuml\nstart\n:New;\nstop\n@enduml"
    mock_session.commit.assert_awaited_once()  # type: ignore[no-untyped-call]
