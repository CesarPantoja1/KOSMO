from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository
from kosmo.domain.sdd.document_converters import document_to_markdown, markdown_to_document
from kosmo.infrastructure.persistence.postgres.models import DiscoveryDocumentModel


class SqlAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_discovery(self, project_id: ProjectId) -> RichTextDocument | None:
        async with self._session_factory() as session:
            stmt = select(DiscoveryDocumentModel).where(
                DiscoveryDocumentModel.project_id == str(project_id)
            )
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
        async with self._session_factory() as session:
            stmt = select(DiscoveryDocumentModel).where(
                DiscoveryDocumentModel.project_id == str(project_id)
            )
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

            await session.commit()
            return document

    async def get_requirements(self, feature_id: object) -> RichTextDocument | None:
        _ = feature_id
        return None

    async def save_requirements(
        self,
        feature_id: object,
        document: RichTextDocument,
    ) -> RichTextDocument:
        _ = feature_id
        return document
