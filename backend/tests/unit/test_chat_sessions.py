from __future__ import annotations

import pytest

from kosmo.application.chat.chat_sessions import (
    CreateChatSessionInput,
    CreateChatSessionUseCase,
    ListChatSessionsInput,
    ListChatSessionsUseCase,
)
from kosmo.contracts.chat import ChatMessageId, ChatRole, MensajeChat
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from tests.unit.fakes import InMemoryChatRepository


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_session_uses_cht_prefix_and_persists() -> None:
    # Arrange
    repo = InMemoryChatRepository()
    uc = CreateChatSessionUseCase(repo)

    # Act
    session = await uc.execute(CreateChatSessionInput(project_id=ProjectId("prj_01"), phase=SpecPhase.DESCUBRIMIENTO))

    # Assert
    assert str(session.id).startswith("cht_")
    assert session.project_id == ProjectId("prj_01")
    assert len(repo.sessions) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_sessions_returns_summaries_with_message_counts() -> None:
    # Arrange
    repo = InMemoryChatRepository()
    create = CreateChatSessionUseCase(repo)
    first = await create.execute(CreateChatSessionInput(project_id=ProjectId("prj_01"), phase=SpecPhase.DESCUBRIMIENTO))
    await repo.save_message(
        ProjectId("prj_01"),
        SpecPhase.DESCUBRIMIENTO,
        MensajeChat(id=ChatMessageId("m1"), role=ChatRole.USER, content="hola"),
        session_id=first.id,
    )
    await repo.save_message(
        ProjectId("prj_01"),
        SpecPhase.DESCUBRIMIENTO,
        MensajeChat(id=ChatMessageId("m2"), role=ChatRole.ASSISTANT, content="respuesta"),
        session_id=first.id,
    )
    second = await create.execute(
        CreateChatSessionInput(project_id=ProjectId("prj_01"), phase=SpecPhase.DESCUBRIMIENTO)
    )

    # Act
    summaries = await ListChatSessionsUseCase(repo).execute(
        ListChatSessionsInput(project_id=ProjectId("prj_01"), phase=SpecPhase.DESCUBRIMIENTO)
    )

    # Assert
    assert len(summaries) == 2
    by_id = {str(s.id): s for s in summaries}
    assert by_id[str(first.id)].message_count == 2
    assert by_id[str(second.id)].message_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_sessions_filters_by_phase() -> None:
    # Arrange
    repo = InMemoryChatRepository()
    create = CreateChatSessionUseCase(repo)
    await create.execute(CreateChatSessionInput(project_id=ProjectId("prj_01"), phase=SpecPhase.DESCUBRIMIENTO))
    await create.execute(CreateChatSessionInput(project_id=ProjectId("prj_01"), phase=SpecPhase.CARACTERISTICAS))

    # Act
    discovery_sessions = await ListChatSessionsUseCase(repo).execute(
        ListChatSessionsInput(project_id=ProjectId("prj_01"), phase=SpecPhase.DESCUBRIMIENTO)
    )
    features_sessions = await ListChatSessionsUseCase(repo).execute(
        ListChatSessionsInput(project_id=ProjectId("prj_01"), phase=SpecPhase.CARACTERISTICAS)
    )

    # Assert
    assert len(discovery_sessions) == 1
    assert len(features_sessions) == 1
    assert discovery_sessions[0].phase == SpecPhase.DESCUBRIMIENTO
    assert features_sessions[0].phase == SpecPhase.CARACTERISTICAS
