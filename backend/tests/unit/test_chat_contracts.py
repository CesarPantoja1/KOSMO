from datetime import UTC, datetime

import pytest

from kosmo.contracts import (
    ChatMessageId,
    ChatRole,
    DiffCambio,
    EstadoPlanCambio,
    MensajeChat,
    PlanCambio,
    PlanChangeId,
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


def test_plan_cambio_default_values():
    diff = DiffCambio(before="nacional", after="LATAM")
    cambio = PlanCambio(
        id=PlanChangeId("chg_100"),
        section="§2 Alcance del producto",
        description="Ampliar alcance a LATAM",
        diff=diff,
    )

    assert cambio.id == "chg_100"
    assert cambio.section == "§2 Alcance del producto"
    assert cambio.description == "Ampliar alcance a LATAM"
    assert cambio.diff.before == "nacional"
    assert cambio.diff.after == "LATAM"
    assert cambio.status == EstadoPlanCambio.PENDING
    assert cambio.status == "pending"
    assert cambio.origin == "Chat Descubrimiento"
    assert cambio.rationale is None
    assert cambio.user_version is None


def test_plan_cambio_full_attributes_and_immutability():
    diff = DiffCambio(before="v1", after="v2")
    cambio = PlanCambio(
        id=PlanChangeId("chg_101"),
        section="§3 Monedas",
        description="Soporte multimoneda",
        diff=diff,
        status=EstadoPlanCambio.CONFLICT,
        origin="Chat Descubrimiento",
        rationale="Cambiaste §2 de nacionales a LATAM.",
        user_version="v1_manual",
    )

    assert cambio.status == EstadoPlanCambio.CONFLICT
    assert cambio.origin == "Chat Descubrimiento"
    assert cambio.rationale == "Cambiaste §2 de nacionales a LATAM."
    assert cambio.user_version == "v1_manual"

    with pytest.raises(AttributeError):
        cambio.status = EstadoPlanCambio.ACCEPTED  # type: ignore[misc]

