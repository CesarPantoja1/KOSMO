from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, cast

import structlog

from kosmo.contracts.auth.context import current_user_id
from kosmo.contracts.sdd.codegen import OpenCodeEvent, OpenCodeEventType

if TYPE_CHECKING:
    from redis.asyncio import Redis

_log = structlog.get_logger(__name__)


class StreamUseCase(Protocol):
    """Cualquier use case con flujo de eventos compatible con el broker (duck-typed)."""

    def execute_stream(self, input_data: object) -> AsyncGenerator[OpenCodeEvent]: ...


class ImplementationEventBroker:
    """Broker en memoria o distribuido (Redis Streams) para enrutar eventos de generación SSE."""

    def __init__(self, history_ttl_seconds: float = 300, redis: Redis | None = None) -> None:
        self._redis = redis
        # Colas activas por cada id de implementación (puede haber múltiples subscriptores locales)
        self._queues: dict[str, list[asyncio.Queue[OpenCodeEvent | None]]] = {}
        # Historial en memoria de eventos ya emitidos (para fallback / entornos locales)
        self._history: dict[str, list[OpenCodeEvent]] = {}
        # Tasks en ejecución en este proceso
        self._tasks: dict[str, asyncio.Task[None]] = {}
        # Project owner checks must also work between the POST that starts a
        # generation and the asynchronous creation of its DB record.
        self._project_ids: dict[str, str] = {}
        # Tasks de purga del historial programadas al terminar cada generación
        self._cleanup_tasks: set[asyncio.Task[None]] = set()
        self._history_ttl_seconds = history_ttl_seconds

    @property
    def is_distributed(self) -> bool:
        return self._redis is not None

    def _serialize_event(self, event: OpenCodeEvent) -> dict[str, str]:
        event_type = getattr(event.event_type, "value", str(event.event_type))
        return {
            "event_type": event_type,
            "session_id": event.session_id,
            "data": json.dumps(event.data),
            "timestamp": event.timestamp.isoformat(),
            "run_id": event.run_id,
        }

    def _deserialize_event(self, fields: dict[bytes | str, bytes | str]) -> OpenCodeEvent | None:
        str_fields: dict[str, str] = {
            (k.decode("utf-8") if isinstance(k, bytes) else str(k)): (
                v.decode("utf-8") if isinstance(v, bytes) else str(v)
            )
            for k, v in fields.items()
        }
        if "_done" in str_fields:
            return None

        event_type_raw = str_fields.get("event_type", "")
        try:
            event_type: OpenCodeEventType | str = OpenCodeEventType(event_type_raw)
        except ValueError:
            event_type = event_type_raw

        try:
            data_raw = json.loads(str_fields.get("data", "{}"))
            data: dict[str, Any] = cast(dict[str, Any], data_raw) if isinstance(data_raw, dict) else {}
        except Exception:
            data = {}

        try:
            timestamp = datetime.fromisoformat(str_fields["timestamp"])
        except Exception:
            timestamp = datetime.now(UTC)

        return OpenCodeEvent(
            event_type=event_type,
            session_id=str_fields.get("session_id", ""),
            data=data,
            timestamp=timestamp,
            run_id=str_fields.get("run_id", ""),
        )

    async def _publish(self, implementation_id: str, event: OpenCodeEvent) -> None:
        self._history.setdefault(implementation_id, []).append(event)
        if implementation_id in self._queues:
            for queue in self._queues[implementation_id]:
                queue.put_nowait(event)
        if self._redis is not None:
            try:
                stream_key = f"kosmo:impl:{implementation_id}:events"
                payload = self._serialize_event(event)
                await self._redis.xadd(stream_key, cast(Any, payload), maxlen=1000, approximate=True)
                await self._redis.expire(stream_key, int(self._history_ttl_seconds))
            except Exception:
                _log.exception("implementation_broker.redis_publish_error", implementation_id=implementation_id)

    def _schedule_history_purge(self, implementation_id: str) -> None:
        """Programa la purga del historial de una implementación terminada tras el TTL."""

        async def _purge() -> None:
            await asyncio.sleep(self._history_ttl_seconds)
            self._history.pop(implementation_id, None)
            self._project_ids.pop(implementation_id, None)

        task = asyncio.create_task(_purge())
        self._cleanup_tasks.add(task)
        task.add_done_callback(lambda _: self._cleanup_tasks.discard(task))

    async def _run_implementation(
        self,
        implementation_id: str,
        use_case: object,
        input_data: object,
        *,
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        structlog.contextvars.bind_contextvars(
            implementation_id=implementation_id,
            project_id=project_id,
            user_id=user_id,
        )
        token = current_user_id.set(user_id) if user_id is not None else None
        try:
            _log.info(
                "codegen.task_started",
                implementation_id=implementation_id,
                project_id=project_id,
                user_id=user_id,
            )
            stream = cast(StreamUseCase, use_case)
            async for event in stream.execute_stream(input_data):
                await self._publish(implementation_id, event)
            _log.info(
                "codegen.task_finished",
                implementation_id=implementation_id,
                project_id=project_id,
                user_id=user_id,
            )
        except Exception as exc:
            _log.exception("implementation_broker.run_error", implementation_id=implementation_id)
            await self._publish(
                implementation_id,
                OpenCodeEvent(
                    event_type=OpenCodeEventType.ERROR,
                    session_id="",
                    data={
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                        "implementation_id": implementation_id,
                        "fatal": True,
                    },
                ),
            )
        finally:
            if token is not None:
                current_user_id.reset(token)
            structlog.contextvars.unbind_contextvars("implementation_id", "project_id", "user_id")

            # Publicar marcador de fin en Redis si está configurado
            if self._redis is not None:
                try:
                    stream_key = f"kosmo:impl:{implementation_id}:events"
                    await self._redis.xadd(stream_key, cast(Any, {"_done": "true"}), maxlen=1000, approximate=True)
                    await self._redis.expire(stream_key, int(self._history_ttl_seconds))
                except Exception:
                    _log.exception(
                        "implementation_broker.redis_publish_done_error", implementation_id=implementation_id
                    )

            # Enviar señal de fin (None) a todos los subscriptores locales
            if implementation_id in self._queues:
                for queue in self._queues[implementation_id]:
                    queue.put_nowait(None)

            # Limpiar la tarea terminada
            if implementation_id in self._tasks:
                del self._tasks[implementation_id]

            # El historial queda disponible un tiempo para replay de suscriptores tardíos
            self._schedule_history_purge(implementation_id)

    def start_implementation(
        self,
        implementation_id: str,
        use_case: object,
        input_data: object,
        *,
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Inicia una tarea de flujo (generación o eliminación de código) en background."""
        if implementation_id in self._tasks:
            # Ya está corriendo
            return

        effective_user_id = user_id or current_user_id.get()

        if project_id is not None:
            self._project_ids[implementation_id] = project_id
            if self._redis is not None:

                async def _persist_project_id() -> None:
                    try:
                        assert self._redis is not None
                        await self._redis.set(
                            f"kosmo:impl:{implementation_id}:project_id",
                            project_id,
                            ex=int(self._history_ttl_seconds),
                        )
                    except Exception:
                        _log.warning(
                            "implementation_broker.redis_set_project_id_failed", implementation_id=implementation_id
                        )

                pid_task = asyncio.create_task(_persist_project_id())
                self._cleanup_tasks.add(pid_task)
                pid_task.add_done_callback(lambda _: self._cleanup_tasks.discard(pid_task))

        task = asyncio.create_task(
            self._run_implementation(
                implementation_id,
                use_case,
                input_data,
                project_id=project_id,
                user_id=effective_user_id,
            )
        )
        self._tasks[implementation_id] = task

    def project_id_for(self, implementation_id: str) -> str | None:
        """Returns the project recorded for an active or recently-finished run."""
        return self._project_ids.get(implementation_id)

    async def get_project_id(self, implementation_id: str) -> str | None:
        """Obtiene el project_id comprobando la memoria local y Redis."""
        if implementation_id in self._project_ids:
            return self._project_ids[implementation_id]
        if self._redis is not None:
            try:
                raw = await self._redis.get(f"kosmo:impl:{implementation_id}:project_id")
                if raw is not None:
                    pid = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
                    self._project_ids[implementation_id] = pid
                    return pid
            except Exception:
                _log.warning("implementation_broker.redis_get_project_id_failed", implementation_id=implementation_id)
        return None

    async def _subscribe_redis(self, implementation_id: str) -> AsyncGenerator[OpenCodeEvent]:
        assert self._redis is not None
        stream_key = f"kosmo:impl:{implementation_id}:events"
        last_id = "0-0"
        idle_time = 0.0
        idle_timeout = self._history_ttl_seconds

        while True:
            try:
                entries_response = await self._redis.xread(
                    streams={stream_key: last_id},
                    count=50,
                    block=1000,
                )
            except Exception as exc:
                _log.warning(
                    "implementation_broker.redis_xread_error", error=str(exc), implementation_id=implementation_id
                )
                break

            if entries_response:
                idle_time = 0.0
                for _stream_name, messages in entries_response:
                    for message_id, fields in messages:
                        last_id = message_id.decode("utf-8") if isinstance(message_id, bytes) else str(message_id)
                        event = self._deserialize_event(fields)
                        if event is None:
                            # Marcador _done recibido: la generación ha concluido
                            return
                        yield event
            else:
                idle_time += 1.0
                if idle_time >= idle_timeout:
                    _log.warning("implementation_broker.redis_stream_idle_timeout", implementation_id=implementation_id)
                    break
                if idle_time >= 3.0:
                    try:
                        if not await self._redis.exists(stream_key):
                            break
                    except Exception:
                        pass

    async def subscribe(self, implementation_id: str) -> AsyncGenerator[OpenCodeEvent]:
        """Se suscribe al flujo de eventos para una implementación dada."""
        if self._redis is not None:
            async for event in self._subscribe_redis(implementation_id):
                yield event
            return

        q: asyncio.Queue[OpenCodeEvent | None] = asyncio.Queue()

        if implementation_id not in self._queues:
            self._queues[implementation_id] = []
        self._queues[implementation_id].append(q)

        try:
            # 1. Emitir eventos históricos
            history = self._history.get(implementation_id, [])
            for event in history:
                yield event

            # 2. Si la tarea ya terminó (o nunca existió), el historial es todo lo que hay
            if implementation_id not in self._tasks:
                return

            # 3. Escuchar nuevos eventos
            while True:
                event = await q.get()
                if event is None:
                    break
                yield event
        finally:
            # Limpieza al desconectar
            if implementation_id in self._queues and q in self._queues[implementation_id]:
                self._queues[implementation_id].remove(q)
                if not self._queues[implementation_id]:
                    del self._queues[implementation_id]

    async def aclose(self) -> None:
        """Cancela todas las tareas de ejecución y purga en curso al apagar el servidor."""
        for task in list(self._tasks.values()):
            task.cancel()
        for task in list(self._cleanup_tasks):
            task.cancel()
        self._tasks.clear()
        self._cleanup_tasks.clear()
        self._queues.clear()
        self._history.clear()
        self._project_ids.clear()


# Instancia por defecto mantenida para compatibilidad
broker = ImplementationEventBroker()
