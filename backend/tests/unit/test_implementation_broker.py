from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from kosmo.application.codegen.generate_feature_implementation import (
    GenerateFeatureImplementationInput,
)
from kosmo.contracts.sdd.codegen import OpenCodeEvent, OpenCodeEventType
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.infrastructure.api.implementation_broker import ImplementationEventBroker


class HappyUseCase:
    """Emite dos eventos y termina."""

    async def execute_stream(
        self,
        input_data: GenerateFeatureImplementationInput,
    ) -> AsyncIterator[OpenCodeEvent]:
        yield OpenCodeEvent(event_type=OpenCodeEventType.PLAN_PROGRESS, session_id="sess_1", data={})
        yield OpenCodeEvent(event_type=OpenCodeEventType.DONE, session_id="sess_1", data={})


class RaisingUseCase:
    """Lanza una excepción al iterar."""

    async def execute_stream(
        self,
        input_data: GenerateFeatureImplementationInput,
    ) -> AsyncIterator[OpenCodeEvent]:
        raise RuntimeError("db down")
        yield  # pragma: no cover — hace del método un async generator


def _input_data() -> GenerateFeatureImplementationInput:
    return GenerateFeatureImplementationInput(feature_id=FeatureId("feat_01"))


async def _collect(broker: ImplementationEventBroker, implementation_id: str) -> list[OpenCodeEvent]:
    events: list[OpenCodeEvent] = []
    async for event in broker.subscribe(implementation_id):
        events.append(event)
    return events


@pytest.mark.asyncio
@pytest.mark.unit
async def test_broker_entrega_eventos_del_use_case() -> None:
    # Arrange
    broker = ImplementationEventBroker()
    broker.start_implementation("impl_1", HappyUseCase(), _input_data())

    # Act
    events = await _collect(broker, "impl_1")

    # Assert
    assert [e.event_type for e in events] == [OpenCodeEventType.PLAN_PROGRESS, OpenCodeEventType.DONE]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_broker_emite_evento_error_cuando_use_case_lanza() -> None:
    # Arrange
    broker = ImplementationEventBroker()
    broker.start_implementation("impl_2", RaisingUseCase(), _input_data())
    task = broker._tasks["impl_2"]

    # Act
    await task
    events = await _collect(broker, "impl_2")

    # Assert
    assert len(events) == 1
    error_event = events[0]
    assert error_event.event_type == OpenCodeEventType.ERROR
    assert error_event.data["error"] == "db down"
    assert error_event.data["error_type"] == "RuntimeError"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_broker_replay_error_para_suscriptores_tardios() -> None:
    # Arrange
    broker = ImplementationEventBroker()
    broker.start_implementation("impl_3", RaisingUseCase(), _input_data())
    task = broker._tasks["impl_3"]
    await task

    # Act — dos suscriptores distintos reciben el historial
    first = await _collect(broker, "impl_3")
    second = await _collect(broker, "impl_3")

    # Assert
    assert len(first) == 1
    assert len(second) == 1
    assert first[0].event_type == OpenCodeEventType.ERROR
    assert second[0].data["error_type"] == "RuntimeError"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_broker_purges_history_after_ttl() -> None:
    # Arrange
    broker = ImplementationEventBroker(history_ttl_seconds=0)
    broker.start_implementation("impl_ttl", HappyUseCase(), _input_data())

    # Act
    await broker._tasks["impl_ttl"]
    for task in list(broker._cleanup_tasks):
        await task

    # Assert — el historial se purga tras el TTL
    assert "impl_ttl" not in broker._history


@pytest.mark.asyncio
@pytest.mark.unit
async def test_broker_keeps_history_for_replay_until_ttl() -> None:
    # Arrange
    broker = ImplementationEventBroker(history_ttl_seconds=300)
    broker.start_implementation("impl_keep", HappyUseCase(), _input_data())

    # Act
    await broker._tasks["impl_keep"]
    events = await _collect(broker, "impl_keep")

    # Assert — el historial sigue disponible para replay antes del TTL
    assert len(events) == 2
    assert "impl_keep" in broker._history
