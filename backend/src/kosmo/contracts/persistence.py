from __future__ import annotations

from typing import Any, Protocol, Self

from kosmo.contracts.chat import ChatRepository
from kosmo.contracts.consistency import TraceabilityRepository
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)


class OutboxPort(Protocol):
    async def enqueue(self, job_type: str, payload: dict[str, Any]) -> None: ...


class UnitOfWork(Protocol):
    """Gobierna el boundary transaccional de un use case.

    Los repositorios expuestos comparten la sesion del UoW: ninguna operacion
    comitea por su cuenta. El commit ocurre en ``__aexit__`` (salida limpia) o
    explicitamente via ``commit()``. Ante una excepcion se hace rollback.
    """

    projects: ProjectRepository
    documents: DocumentRepository
    features: FeatureRepository
    requirements: RequirementRepository
    diagrams: ActivityDiagramRepository
    chat: ChatRepository
    traceability: TraceabilityRepository
    outbox: OutboxPort

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
