from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from kosmo.application.chat.chat_sessions import (
    DeleteChatSessionInput,
    DeleteChatSessionUseCase,
)
from kosmo.contracts.sdd.ids import ChatSessionId


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_chat_session_delegates_with_correct_id() -> None:
    # Arrange
    chat_repo = AsyncMock()
    chat_repo.delete_session = AsyncMock(return_value=None)
    use_case = DeleteChatSessionUseCase(chat_repo=chat_repo)

    # Act
    await use_case.execute(DeleteChatSessionInput(session_id=ChatSessionId("cht_01")))

    # Assert
    chat_repo.delete_session.assert_awaited_once_with(ChatSessionId("cht_01"))


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_chat_session_is_idempotent_when_repo_returns_none() -> None:
    # Arrange
    chat_repo = AsyncMock()
    chat_repo.delete_session = AsyncMock(return_value=None)
    use_case = DeleteChatSessionUseCase(chat_repo=chat_repo)

    # Act & Assert — borrar una sesión inexistente no lanza
    await use_case.execute(DeleteChatSessionInput(session_id=ChatSessionId("cht_missing")))


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_chat_session_propagates_repo_errors() -> None:
    # Arrange
    chat_repo = AsyncMock()
    chat_repo.delete_session = AsyncMock(side_effect=RuntimeError("db down"))
    use_case = DeleteChatSessionUseCase(chat_repo=chat_repo)

    # Act & Assert
    with pytest.raises(RuntimeError, match="db down"):
        await use_case.execute(DeleteChatSessionInput(session_id=ChatSessionId("cht_01")))
