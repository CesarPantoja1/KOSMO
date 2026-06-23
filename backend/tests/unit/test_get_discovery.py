import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.discovery.get_discovery import (
    GetDiscoveryInput,
    GetDiscoveryOutput,
    GetDiscoveryUseCase,
)
from kosmo.contracts.sdd.document import (
    DocumentNode,
    RichTextDocument,
    SectionHeading,
)
from kosmo.contracts.sdd.errors import DocumentNotFoundError
from kosmo.contracts.sdd.ids import ProjectId


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.documents: dict[str, RichTextDocument] = {}

    async def get_discovery(self, project_id: ProjectId) -> RichTextDocument | None:
        return self.documents.get(str(project_id))

    async def save_discovery(
        self, project_id: ProjectId, document: RichTextDocument
    ) -> RichTextDocument:
        self.documents[str(project_id)] = document
        return document

    async def get_requirements(self, feature_id: Any) -> RichTextDocument | None:  # noqa: ARG002
        return None

    async def save_requirements(
        self, feature_id: Any, document: RichTextDocument  # noqa: ARG002
    ) -> RichTextDocument:
        return document


def _make_discovery_document() -> RichTextDocument:
    return RichTextDocument(
        nodes=[
            DocumentNode(
                type="heading",
                heading=SectionHeading(text="Introducción", level=2, slug="introduccion"),
                content="Contenido de introducción",
            ),
            DocumentNode(
                type="heading",
                heading=SectionHeading(text="Objetivos", level=2, slug="objetivos"),
                content="Contenido de objetivos",
            ),
        ]
    )


@pytest.mark.asyncio
async def test_get_discovery_returns_document_when_exists() -> None:
    # Arrange
    repository: Any = InMemoryDocumentRepository()
    project_id = ProjectId("prj_test456")
    doc = _make_discovery_document()
    await repository.save_discovery(project_id, doc)
    use_case = GetDiscoveryUseCase(document_repo=repository)

    # Act
    result = await use_case.execute(GetDiscoveryInput(project_id=project_id))

    # Assert
    assert isinstance(result, GetDiscoveryOutput)
    assert result.project_id == project_id
    assert result.document is not None
    assert result.document.section_count == 2


@pytest.mark.asyncio
async def test_get_discovery_raises_document_not_found_when_missing() -> None:
    # Arrange
    repository: Any = InMemoryDocumentRepository()
    use_case = GetDiscoveryUseCase(document_repo=repository)

    # Act & Assert
    with pytest.raises(DocumentNotFoundError) as exc_info:
        await use_case.execute(GetDiscoveryInput(project_id=ProjectId("prj_missing")))

    assert "discovery" in str(exc_info.value.problem.detail)
    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
async def test_get_discovery_returns_empty_document_when_no_sections() -> None:
    # Arrange
    repository: Any = InMemoryDocumentRepository()
    project_id = ProjectId("prj_empty")
    empty_doc = RichTextDocument(nodes=[])
    await repository.save_discovery(project_id, empty_doc)
    use_case = GetDiscoveryUseCase(document_repo=repository)

    # Act
    result = await use_case.execute(GetDiscoveryInput(project_id=project_id))

    # Assert
    assert result.document.section_count == 0
