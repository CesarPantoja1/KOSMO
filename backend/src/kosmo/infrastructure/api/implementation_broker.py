import asyncio
from collections.abc import AsyncGenerator

import structlog

from kosmo.application.codegen.generate_feature_implementation import (
    GenerateFeatureImplementationInput,
    GenerateFeatureImplementationUseCase,
)
from kosmo.contracts.codegen import OpenCodeEvent, OpenCodeEventType

_log = structlog.get_logger(__name__)


class ImplementationEventBroker:
    """Broker en memoria para enrutar eventos de generación de código SSE.

    Dado que FastAPI maneja cada petición en su propio ciclo, usamos este
    singleton para que el POST inicial delegue la ejecución y guarde los
    eventos en colas de asyncio que luego el GET consumirá en streaming.
    """

    def __init__(self) -> None:
        # Colas activas por cada id de implementación (puede haber múltiples subscriptores)
        self._queues: dict[str, list[asyncio.Queue[OpenCodeEvent | None]]] = {}
        # Historial de eventos ya emitidos para esta implementación (por si el GET llega tarde)
        self._history: dict[str, list[OpenCodeEvent]] = {}
        # Tasks en ejecución
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def _publish(self, implementation_id: str, event: OpenCodeEvent) -> None:
        self._history.setdefault(implementation_id, []).append(event)
        if implementation_id in self._queues:
            for queue in self._queues[implementation_id]:
                queue.put_nowait(event)

    async def _run_implementation(
        self,
        implementation_id: str,
        use_case: GenerateFeatureImplementationUseCase,
        input_data: GenerateFeatureImplementationInput,
    ) -> None:
        try:
            async for event in use_case.execute_stream(input_data):
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

    def start_implementation(
        self,
        implementation_id: str,
        use_case: GenerateFeatureImplementationUseCase,
        input_data: GenerateFeatureImplementationInput,
    ) -> None:
        """Inicia la generación en background."""
        if implementation_id in self._tasks:
            # Ya está corriendo
            return

        task = asyncio.create_task(self._run_implementation(implementation_id, use_case, input_data))
        self._tasks[implementation_id] = task

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
