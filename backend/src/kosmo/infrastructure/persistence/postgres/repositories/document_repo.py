from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.sdd.document import RichTextDocument, SpecPhase
from kosmo.contracts.sdd.ids import PlanChangeId, ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository
from kosmo.domain.sdd.document_converters import document_to_markdown, markdown_to_document
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.models import DiscoveryDocumentModel, DocumentVersionModel


class SqlAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_discovery(self, project_id: ProjectId) -> RichTextDocument | None:
        async with self._session_factory() as session:
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
        *,
        _session: AsyncSession | None = None,
    ) -> RichTextDocument:
        markdown = document_to_markdown(document)

        if _session is not None:
            stmt = select(DiscoveryDocumentModel).where(DiscoveryDocumentModel.project_id == str(project_id))
            result = await _session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                model = DiscoveryDocumentModel(project_id=str(project_id), markdown=markdown)
                _session.add(model)
            else:
                model.markdown = markdown
                model.updated_at = datetime.now(UTC)
            return document

        async with self._session_factory() as session:
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

            await session.commit()
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
        change_ids: list[PlanChangeId],
        *,
        _session: AsyncSession | None = None,
    ) -> str:
        version_id = IdGenerator.generate("doc_version")
        model = DocumentVersionModel(
            id=version_id,
            project_id=str(project_id),
            phase=phase.value,
            markdown=markdown,
            change_ids=[str(cid) for cid in change_ids],
        )
        if _session is not None:
            _session.add(model)
            return version_id

        async with self._session_factory() as session:
            session.add(model)
            await session.commit()
            return version_id

    async def get_version(self, version_id: str) -> str | None:
        async with self._session_factory() as session:
            stmt = select(DocumentVersionModel).where(DocumentVersionModel.id == version_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            return model.markdown if model else None
