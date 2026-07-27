from datetime import UTC, datetime

import pytest

from kosmo.contracts import (
    ChatMessageId,
    ChatRole,
    DiffCambio,
    MensajeChat,
    SugerenciaCambio,
)


def test_mensaje_chat_creation_without_suggested_change():
    msg = MensajeChat(
        id=ChatMessageId("msg_001"),
        role=ChatRole.USER,
        content="Amplía el alcance a LATAM",
    )

    assert msg.id == "msg_001"
    assert msg.role == ChatRole.USER
    assert msg.role == "user"
    assert msg.content == "Amplía el alcance a LATAM"
    assert msg.suggested_change is None
    assert isinstance(msg.timestamp, datetime)
    assert msg.timestamp.tzinfo == UTC


def test_mensaje_chat_creation_with_suggested_change():
    diff = DiffCambio(
        before="viajes nacionales dentro del país",
        after="viajes y vuelos dentro de la región LATAM",
    )
    sugerencia = SugerenciaCambio(
        id="chg_01KT",
        section="§2 Alcance del producto",
        description="Ampliar alcance de 'nacionales' a 'LATAM'",
        diff=diff,
    )
    msg = MensajeChat(
        id=ChatMessageId("msg_002"),
        role=ChatRole.ASSISTANT,
        content="He ampliado la sección de alcance.",
        suggested_change=sugerencia,
    )

    assert msg.id == "msg_002"
    assert msg.role == ChatRole.ASSISTANT
    assert msg.suggested_change is not None
    assert msg.suggested_change.id == "chg_01KT"
    assert msg.suggested_change.section == "§2 Alcance del producto"
    assert msg.suggested_change.diff.before == "viajes nacionales dentro del país"
    assert msg.suggested_change.diff.after == "viajes y vuelos dentro de la región LATAM"


def test_mensaje_chat_immutability():
    msg = MensajeChat(
        id=ChatMessageId("msg_003"),
        role=ChatRole.SYSTEM,
        content="Contexto del sistema inicializado",
    )

    with pytest.raises(AttributeError):
        msg.content = "Nuevo contenido"  # type: ignore[misc]
