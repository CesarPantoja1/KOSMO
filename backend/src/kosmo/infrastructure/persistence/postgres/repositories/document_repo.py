from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.sdd.document import RichTextDocument, SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository
from kosmo.domain.sdd.document_converters import document_to_markdown, markdown_to_document
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.models import DiscoveryDocumentModel, DocumentVersionModel


class SqlAlchemyDocumentRepository(DocumentRepository):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        if session_factory is None and session is None:
            raise ValueError("Se requiere session_factory o session")
        self._session_factory = session_factory
        self._session = session

    @asynccontextmanager
    async def _session_ctx(self) -> AsyncGenerator[AsyncSession]:
        if self._session is not None:
            yield self._session
            return
        assert self._session_factory is not None
        async with self._session_factory() as session:
            yield session

    async def _commit(self, session: AsyncSession) -> None:
        if self._session is None:
            await session.commit()

    async def get_discovery(self, project_id: ProjectId) -> RichTextDocument | None:
        async with self._session_ctx() as session:
            stmt = select(DiscoveryDocumentModel).where(DiscoveryDocumentModel.project_id == str(project_id))
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return markdown_to_document(model.markdown)

    async def save_discovery(
        self,
        project_id: ProjectId,
        document: RichTextDocument,
    ) -> RichTextDocument:
        markdown = document_to_markdown(document)

        async with self._session_ctx() as session:
            stmt = select(DiscoveryDocumentModel).where(DiscoveryDocumentModel.project_id == str(project_id))
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                model = DiscoveryDocumentModel(
                    project_id=str(project_id),
                    markdown=markdown,
                )
                session.add(model)
            else:
                model.markdown = markdown
                model.updated_at = datetime.now(UTC)

            await self._commit(session)
            return document

    async def get_requirements(  # type: ignore[override]
        self, feature_id: object
    ) -> RichTextDocument | None:
        _ = feature_id
        return None

    async def save_requirements(  # type: ignore[override]
        self,
        feature_id: object,
        document: RichTextDocument,
    ) -> RichTextDocument:
        _ = feature_id
        return document

    async def save_version(  # type: ignore[override]
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        markdown: str,
        change_ids: list[str],
    ) -> str:
        version_id = IdGenerator.generate("doc_version")
        model = DocumentVersionModel(
            id=version_id,
            project_id=str(project_id),
            phase=phase.value,
            markdown=markdown,
            change_ids=[str(cid) for cid in change_ids],
        )
        async with self._session_ctx() as session:
            session.add(model)
            await self._commit(session)
            return version_id

    async def get_version(self, version_id: str) -> str | None:
        async with self._session_ctx() as session:
            stmt = select(DocumentVersionModel).where(DocumentVersionModel.id == version_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            return model.markdown if model else None

    async def get_latest_version(self, project_id: ProjectId, phase: object) -> str | None:  # type: ignore[override]
        phase_value = phase.value if hasattr(phase, "value") else str(phase)  # type: ignore[reportUnknownVariableType, reportUnknownMemberType]  # noqa: E501
        async with self._session_ctx() as session:
            stmt = (
                select(DocumentVersionModel)
                .where(
                    DocumentVersionModel.project_id == str(project_id),
                    DocumentVersionModel.phase == phase_value,  # type: ignore[reportUnknownArgumentType]
                )
                .order_by(DocumentVersionModel.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            return model.markdown if model else None
