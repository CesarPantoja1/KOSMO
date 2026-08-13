from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from kosmo.contracts.chat import ChatRepository
from kosmo.contracts.consistency import TraceabilityRepository
from kosmo.contracts.persistence import OutboxPort
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)
from kosmo.infrastructure.persistence.postgres.outbox import OutboxStore
from kosmo.infrastructure.persistence.postgres.repositories.activity_diagram_repo import (
    SqlAlchemyActivityDiagramRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.chat_repo import SqlAlchemyChatRepository
from kosmo.infrastructure.persistence.postgres.repositories.document_repo import (
    SqlAlchemyDocumentRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.feature_repo import (
    SqlAlchemyFeatureRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.project_repo import (
    SqlAlchemyProjectRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.requirement_repo import (
    SqlAlchemyRequirementRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.traceability_repo import (
    SqlAlchemyTraceabilityRepository,
)


class SqlAlchemyUnitOfWork:
    """Unit of Work sobre SQLAlchemy: una sesion compartida por repos bound.

    Cada ``__aenter__`` crea una sesion fresca y repos bound a ella. Ninguna
    operacion de repos comitea por su cuenta: el commit ocurre al salir del
    contexto (salida limpia) o via ``commit()``; ante excepcion, rollback.
    """

    projects: ProjectRepository
    documents: DocumentRepository
    features: FeatureRepository
    requirements: RequirementRepository
    diagrams: ActivityDiagramRepository
    chat: ChatRepository
    traceability: TraceabilityRepository
    outbox: OutboxPort

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self.projects = SqlAlchemyProjectRepository(session=self._session)
        self.documents = SqlAlchemyDocumentRepository(session=self._session)
        self.features = SqlAlchemyFeatureRepository(session=self._session)
        self.requirements = SqlAlchemyRequirementRepository(session=self._session)
        self.diagrams = SqlAlchemyActivityDiagramRepository(session=self._session)
        self.chat = SqlAlchemyChatRepository(session=self._session)
        self.traceability = SqlAlchemyTraceabilityRepository(session=self._session)
        self.outbox = OutboxStore(session=self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        if self._session is None:
            return
        if exc_type is None:
            await self._session.commit()
        else:
            await self._session.rollback()
        await self._session.close()
        self._session = None

    async def commit(self) -> None:
        if self._session is None:
            raise ValueError("Unit of Work no activo")
        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise ValueError("Unit of Work no activo")
        await self._session.rollback()
