from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from kosmo.application.chat.process_chat_regeneration import (
    ProcessChatRegenerationInput,
    ProcessChatRegenerationOutput,
    ProcessChatRegenerationUseCase,
)
from kosmo.application.chat.validate_phase_context import (
    ValidatePhaseContextUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.chat import ChatRole, MensajeChat, ModificacionChat
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import DocumentNotFoundError, FeatureNotFoundError
from kosmo.contracts.sdd.ids import ChatMessageId, ProjectId
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.api.routers.discovery import process_chat_message as discovery_chat
from kosmo.infrastructure.api.routers.feature_chat import (
    process_feature_chat_message as feature_chat,
)
from kosmo.infrastructure.api.routers.requirement_chat import (
    process_requirement_chat_message as requirement_chat,
)
from kosmo.infrastructure.api.schemas import ChatResponse, SendChatRequest

_REAL_VALIDATE_UC = ValidatePhaseContextUseCase()


def _principal() -> Principal:
    return Principal(subject="usr_test123", scopes=frozenset({"*"}))


def _assistant_message(content: str = "Se aplicó el cambio.") -> MensajeChat:
    return MensajeChat(
        id=ChatMessageId(IdGenerator.generate("chat_message")),
        role=ChatRole.ASSISTANT,
        content=content,
        modification=ModificacionChat(
            applied=True,
            modified_section="Público objetivo",
            change_description=content,
            modified_document="# Doc\n\nActualizado",
            before="# Doc",
            after="# Doc\n\nActualizado",
        ),
    )


def _make_mock_uc(output: ProcessChatRegenerationOutput | None = None, exc: Exception | None = None) -> MagicMock:
    uc = MagicMock(spec=ProcessChatRegenerationUseCase)
    if exc:
        uc.execute = AsyncMock(side_effect=exc)
    else:
        uc.execute = AsyncMock(return_value=output)
    return uc


@pytest.mark.unit
@pytest.mark.asyncio
async def test_discovery_chat_returns_chat_response_with_modification() -> None:
    # Arrange
    output = ProcessChatRegenerationOutput(
        project_id=ProjectId("prj_01"),
        message=_assistant_message(),
        modification=_assistant_message().modification,
        downstream_impact=[{"id": "imp_01", "phase": "features", "targetId": "feat_01", "artifact_type": "Feature"}],
    )
    uc = _make_mock_uc(output)
    payload = SendChatRequest(content="Cambia el público objetivo a pymes")

    # Act
    response = await discovery_chat("prj_01", payload, _principal(), uc, _REAL_VALIDATE_UC)

    # Assert
    assert isinstance(response, ChatResponse)
    assert response.modification is not None
    assert response.modification.applied is True
    assert response.modification.modified_section == "Público objetivo"
    assert response.consistency is not None
    assert len(response.consistency) == 1
    assert response.redirect is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_discovery_chat_returns_redirect_when_message_belongs_to_other_phase() -> None:
    # Arrange
    uc = _make_mock_uc()
    payload = SendChatRequest(content="Agrega la característica de login al sistema")

    # Act
    response = await discovery_chat("prj_01", payload, _principal(), uc, _REAL_VALIDATE_UC)

    # Assert
    assert isinstance(response, ChatResponse)
    assert response.redirect is not None
    assert response.redirect.target_phase == "caracteristicas"
    assert response.modification is None
    uc.execute.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_feature_chat_redirects_business_change_to_discovery() -> None:
    # Arrange
    uc = _make_mock_uc()
    payload = SendChatRequest(content="Cambia el giro del negocio a venta de suscripciones")

    # Act
    response = await feature_chat("feat_01", payload, _principal(), uc, _REAL_VALIDATE_UC)

    # Assert
    assert isinstance(response, ChatResponse)
    assert response.redirect is not None
    assert response.redirect.target_phase == "descubrimiento"
    assert response.modification is None
    uc.execute.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_feature_chat_applies_modification_and_derives_project() -> None:
    # Arrange
    output = ProcessChatRegenerationOutput(
        project_id=ProjectId("prj_01"),
        message=_assistant_message("Título actualizado."),
        modification=_assistant_message().modification,
    )
    uc = _make_mock_uc(output)
    payload = SendChatRequest(content="Cambia el título a 'Registrar y editar gastos'")

    # Act
    response = await feature_chat("feat_01", payload, _principal(), uc, _REAL_VALIDATE_UC)

    # Assert
    assert isinstance(response, ChatResponse)
    assert response.modification is not None
    assert response.modification.applied is True

    input_data = uc.execute.await_args.args[0]
    assert isinstance(input_data, ProcessChatRegenerationInput)
    assert input_data.document_id == "feat_01"
    assert input_data.document_type == SpecPhase.CARACTERISTICAS
    assert input_data.project_id is None
    assert input_data.context_id == "feat_01"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_requirement_chat_applies_modification() -> None:
    # Arrange
    output = ProcessChatRegenerationOutput(
        project_id=ProjectId("prj_01"),
        message=_assistant_message("REQ-1.1 actualizado."),
        modification=_assistant_message().modification,
    )
    uc = _make_mock_uc(output)
    payload = SendChatRequest(content="Agrega dos decimales al requisito REQ-1.1")

    # Act
    response = await requirement_chat("feat_01", payload, _principal(), uc, _REAL_VALIDATE_UC)

    # Assert
    assert isinstance(response, ChatResponse)
    assert response.modification is not None
    assert response.modification.applied is True

    input_data = uc.execute.await_args.args[0]
    assert input_data.document_type == SpecPhase.REQUISITOS


@pytest.mark.unit
@pytest.mark.asyncio
async def test_discovery_chat_maps_not_found_to_404() -> None:
    # Arrange
    uc = _make_mock_uc(exc=DocumentNotFoundError(document_type="descubrimiento"))
    payload = SendChatRequest(content="Cambia la visión del producto")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await discovery_chat("prj_01", payload, _principal(), uc, _REAL_VALIDATE_UC)

    assert exc_info.value.status_code == 404


@pytest.mark.unit
@pytest.mark.asyncio
async def test_feature_chat_maps_not_found_to_404() -> None:
    # Arrange
    uc = _make_mock_uc(exc=FeatureNotFoundError(feature_id="feat_missing"))
    payload = SendChatRequest(content="Cambia el título de la característica")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await feature_chat("feat_missing", payload, _principal(), uc, _REAL_VALIDATE_UC)

    assert exc_info.value.status_code == 404
