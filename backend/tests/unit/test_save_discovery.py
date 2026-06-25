import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.discovery.save_discovery import (
    SaveDiscoveryInput,
    SaveDiscoveryOutput,
    SaveDiscoveryUseCase,
)
from kosmo.contracts.sdd.document import DocumentNode, RichTextDocument, SectionHeading
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
        self,
        feature_id: Any,  # noqa: ARG002
        document: RichTextDocument,  # noqa: ARG002
    ) -> RichTextDocument:
        return document


def _make_discovery_document(title: str = "Test Discovery") -> RichTextDocument:
    return RichTextDocument(
        nodes=[
            DocumentNode(
                type="heading",
                heading=SectionHeading(text=title, level=2, slug="test"),
                content="Contenido de prueba",
            ),
        ]
    )


@pytest.mark.asyncio
async def test_save_discovery_persists_document() -> None:
    # Arrange
    repository: Any = InMemoryDocumentRepository()
    use_case = SaveDiscoveryUseCase(document_repo=repository)
    project_id = ProjectId("prj_discovery123")
    doc = _make_discovery_document()

    # Act
    await use_case.execute(SaveDiscoveryInput(project_id=project_id, document=doc))

    # Assert
    saved = await repository.get_discovery(project_id)
    assert saved is not None
    assert saved.nodes[0].heading is not None
    assert saved.nodes[0].heading.text == "Test Discovery"


@pytest.mark.asyncio
async def test_save_discovery_returns_saved_document() -> None:
    # Arrange
    repository: Any = InMemoryDocumentRepository()
    use_case = SaveDiscoveryUseCase(document_repo=repository)
    project_id = ProjectId("prj_discovery456")
    doc = _make_discovery_document("Nuevo Documento")

    # Act
    result = await use_case.execute(SaveDiscoveryInput(project_id=project_id, document=doc))

    # Assert
    assert isinstance(result, SaveDiscoveryOutput)
    assert result.project_id == project_id
    assert result.document.nodes[0].heading is not None
    assert result.document.nodes[0].heading.text == "Nuevo Documento"


@pytest.mark.asyncio
async def test_save_discovery_overwrites_existing_document() -> None:
    # Arrange
    repository: Any = InMemoryDocumentRepository()
    use_case = SaveDiscoveryUseCase(document_repo=repository)
    project_id = ProjectId("prj_overwrite")

    doc1 = _make_discovery_document("Primera Versión")
    doc2 = _make_discovery_document("Segunda Versión")

    # Act
    await use_case.execute(SaveDiscoveryInput(project_id=project_id, document=doc1))
    await use_case.execute(SaveDiscoveryInput(project_id=project_id, document=doc2))

    # Assert
    saved = await repository.get_discovery(project_id)
    assert saved is not None
    assert saved.nodes[0].heading is not None
    assert saved.nodes[0].heading.text == "Segunda Versión"
