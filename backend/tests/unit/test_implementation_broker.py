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


@pytest.mark.asyncio
@pytest.mark.unit
async def test_broker_aclose_cancels_running_and_cleanup_tasks() -> None:
    import asyncio

    # Arrange
    broker = ImplementationEventBroker(history_ttl_seconds=300)

    class HangingUseCase:
        async def execute_stream(
            self,
            input_data: GenerateFeatureImplementationInput,
        ) -> AsyncIterator[OpenCodeEvent]:
            await asyncio.sleep(100)
            yield OpenCodeEvent(event_type=OpenCodeEventType.DONE, session_id="sess_hang", data={})

    broker.start_implementation("impl_hang", HangingUseCase(), _input_data())
    broker._schedule_history_purge("impl_purge")
    assert len(broker._tasks) == 1
    assert len(broker._cleanup_tasks) == 1

    # Act
    await broker.aclose()

    # Assert
    assert len(broker._tasks) == 0
    assert len(broker._queues) == 0
    assert len(broker._history) == 0
    assert len(broker._project_ids) == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_broker_propagates_user_and_project_context() -> None:
    import structlog

    from kosmo.contracts.auth.context import current_user_id

    captured_ctx: dict[str, object] = {}
    captured_user_id: list[str | None] = []

    class ContextCapturingUseCase:
        async def execute_stream(
            self,
            input_data: GenerateFeatureImplementationInput,
        ) -> AsyncIterator[OpenCodeEvent]:
            captured_user_id.append(current_user_id.get())
            captured_ctx.update(structlog.contextvars.get_contextvars())
            yield OpenCodeEvent(event_type=OpenCodeEventType.DONE, session_id="sess_ctx", data={})

    broker = ImplementationEventBroker()
    broker.start_implementation(
        "impl_ctx",
        ContextCapturingUseCase(),
        _input_data(),
        project_id="prj_test_123",
        user_id="usr_test_456",
    )

    task = broker._tasks["impl_ctx"]
    await task

    assert captured_user_id == ["usr_test_456"]
    assert captured_ctx.get("project_id") == "prj_test_123"
    assert captured_ctx.get("user_id") == "usr_test_456"
    assert captured_ctx.get("implementation_id") == "impl_ctx"
    # Ensure cleanup after completion
    assert current_user_id.get() is None


class _FakeRedis:
    """Mock mínimo de Redis para verificar Redis Streams y operaciones de broker."""

    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[bytes, bytes]]]] = {}
        self.kv: dict[str, bytes] = {}
        self.expirations: dict[str, int] = {}
        self._counter = 0

    async def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = False) -> str:
        self._counter += 1
        msg_id = f"{self._counter}-0"
        byte_fields = {
            (k.encode("utf-8") if isinstance(k, str) else k): (v.encode("utf-8") if isinstance(v, str) else v)
            for k, v in fields.items()
        }
        self.streams.setdefault(key, []).append((msg_id, byte_fields))
        return msg_id

    async def xread(
        self, streams: dict[str, str], count: int | None = None, block: int | None = None
    ) -> list[tuple[str, list[tuple[str, dict[bytes, bytes]]]]]:
        results: list[tuple[str, list[tuple[str, dict[bytes, bytes]]]]] = []
        for key, last_id in streams.items():
            entries = self.streams.get(key, [])
            filtered: list[tuple[str, dict[bytes, bytes]]] = []
            for entry_id, fields in entries:
                if last_id == "0-0" or int(entry_id.split("-")[0]) > int(last_id.split("-")[0]):
                    filtered.append((entry_id, fields))
            if count is not None:
                filtered = filtered[:count]
            if filtered:
                results.append((key, filtered))
        return results

    async def expire(self, key: str, seconds: int) -> bool:
        self.expirations[key] = seconds
        return True

    async def exists(self, key: str) -> int:
        return 1 if (key in self.streams or key in self.kv) else 0

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.kv[key] = value.encode("utf-8")
        if ex is not None:
            self.expirations[key] = ex
        return True

    async def get(self, key: str) -> bytes | None:
        return self.kv.get(key)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_broker_distributed_flag_and_redis_stream_flow() -> None:
    from typing import Any, cast

    fake_redis = _FakeRedis()
    broker = ImplementationEventBroker(redis=cast(Any, fake_redis))

    assert broker.is_distributed is True

    # Iniciar implementación en broker 1 (Worker 1)
    broker.start_implementation(
        "impl_redis_1",
        HappyUseCase(),
        _input_data(),
        project_id="prj_redis_99",
        user_id="usr_redis_1",
    )
    task = broker._tasks["impl_redis_1"]
    await task

    # Simular Worker 2 que no tiene estado local en memoria
    worker2_broker = ImplementationEventBroker(redis=cast(Any, fake_redis))
    assert worker2_broker.project_id_for("impl_redis_1") is None

    # Debe recuperar el project_id desde Redis
    resolved_pid = await worker2_broker.get_project_id("impl_redis_1")
    assert resolved_pid == "prj_redis_99"

    # Suscribirse desde Worker 2 consume el stream de Redis Streams
    events = await _collect(worker2_broker, "impl_redis_1")
    assert len(events) == 2
    assert events[0].event_type == OpenCodeEventType.PLAN_PROGRESS
    assert events[1].event_type == OpenCodeEventType.DONE


@pytest.mark.asyncio
@pytest.mark.unit
async def test_broker_serialization_and_deserialization() -> None:
    broker = ImplementationEventBroker()
    event = OpenCodeEvent(
        event_type=OpenCodeEventType.FILE_EDIT,
        session_id="sess_test",
        data={"path": "src/App.tsx", "lines": 42},
    )

    serialized = broker._serialize_event(event)
    assert serialized["event_type"] == "file_edit"
    assert serialized["session_id"] == "sess_test"
    assert '"lines": 42' in serialized["data"]

    deserialized = broker._deserialize_event(
        {
            b"event_type": b"file_edit",
            b"session_id": b"sess_test",
            b"data": b'{"path": "src/App.tsx", "lines": 42}',
            b"timestamp": event.timestamp.isoformat().encode("utf-8"),
            b"run_id": b"run_123",
        }
    )
    assert deserialized is not None
    assert deserialized.event_type == OpenCodeEventType.FILE_EDIT
    assert deserialized.session_id == "sess_test"
    assert deserialized.data["path"] == "src/App.tsx"
    assert deserialized.run_id == "run_123"

    # Terminal marker devuelve None
    terminal = broker._deserialize_event({b"_done": b"true"})
    assert terminal is None
