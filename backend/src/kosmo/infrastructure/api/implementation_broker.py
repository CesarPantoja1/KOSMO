import asyncio
from collections.abc import AsyncGenerator
from typing import Protocol, cast

import structlog

from kosmo.contracts.codegen import OpenCodeEvent, OpenCodeEventType

_log = structlog.get_logger(__name__)


class StreamUseCase(Protocol):
    """Cualquier use case con flujo de eventos compatible con el broker (duck-typed)."""

    def execute_stream(self, input_data: object) -> AsyncGenerator[OpenCodeEvent]: ...


class ImplementationEventBroker:
    """Broker en memoria para enrutar eventos de generación de código SSE.

    Dado que FastAPI maneja cada petición en su propio ciclo, usamos este
    singleton para que el POST inicial delegue la ejecución y guarde los
    eventos en colas de asyncio que luego el GET consumirá en streaming.
    """

    def __init__(self, history_ttl_seconds: float = 300) -> None:
        # Colas activas por cada id de implementación (puede haber múltiples subscriptores)
        self._queues: dict[str, list[asyncio.Queue[OpenCodeEvent | None]]] = {}
        # Historial de eventos ya emitidos para esta implementación (por si el GET llega tarde)
        self._history: dict[str, list[OpenCodeEvent]] = {}
        # Tasks en ejecución
        self._tasks: dict[str, asyncio.Task[None]] = {}
        # Project owner checks must also work between the POST that starts a
        # generation and the asynchronous creation of its DB record.
        self._project_ids: dict[str, str] = {}
        # Tasks de purga del historial programadas al terminar cada generación
        self._cleanup_tasks: set[asyncio.Task[None]] = set()
        self._history_ttl_seconds = history_ttl_seconds

    def _publish(self, implementation_id: str, event: OpenCodeEvent) -> None:
        self._history.setdefault(implementation_id, []).append(event)
        if implementation_id in self._queues:
            for queue in self._queues[implementation_id]:
                queue.put_nowait(event)

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
    ) -> None:
        try:
            stream = cast(StreamUseCase, use_case)
            async for event in stream.execute_stream(input_data):
                self._publish(implementation_id, event)
        except Exception as exc:
            _log.exception("implementation_broker.run_error", implementation_id=implementation_id)
            self._publish(
                implementation_id,
                OpenCodeEvent(
                    event_type=OpenCodeEventType.ERROR,
                    session_id="",
                    data={
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                        "implementation_id": implementation_id,
                    },
                ),
            )
        finally:
            # Enviar señal de fin (None) a todos los subscriptores
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
    ) -> None:
        """Inicia una tarea de flujo (generación o eliminación de código) en background."""
        if implementation_id in self._tasks:
            # Ya está corriendo
            return

        if project_id is not None:
            self._project_ids[implementation_id] = project_id

        task = asyncio.create_task(self._run_implementation(implementation_id, use_case, input_data))
        self._tasks[implementation_id] = task

    def project_id_for(self, implementation_id: str) -> str | None:
        """Returns the project recorded for an active or recently-finished run."""
        return self._project_ids.get(implementation_id)

    async def subscribe(self, implementation_id: str) -> AsyncGenerator[OpenCodeEvent]:
        """Se suscribe al flujo de eventos para una implementación dada."""
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


# Singleton global
broker = ImplementationEventBroker()
