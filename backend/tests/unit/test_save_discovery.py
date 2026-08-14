from typing import Any

import pytest

from kosmo.application.discovery.save_discovery import (
    SaveDiscoveryInput,
    SaveDiscoveryOutput,
    SaveDiscoveryUseCase,
)
from kosmo.contracts.sdd.document import DocumentNode, RichTextDocument, SectionHeading
from kosmo.contracts.sdd.ids import ProjectId
from tests.unit.fakes import InMemoryDocumentRepository, InMemoryOutbox


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
@pytest.mark.unit
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
@pytest.mark.unit
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
@pytest.mark.unit
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


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_discovery_enqueues_downstream_evaluation() -> None:
    # Arrange
    repository: Any = InMemoryDocumentRepository()
    outbox = InMemoryOutbox()
    use_case = SaveDiscoveryUseCase(document_repo=repository, outbox=outbox)
    project_id = ProjectId("prj_chain")

    # Act
    await use_case.execute(SaveDiscoveryInput(project_id=project_id, document=_make_discovery_document()))

    # Assert — editar Descubrimiento dispara la verificación de todas las fases a la derecha
    assert len(outbox.jobs) == 1
    job_type, payload = outbox.jobs[0]
    assert job_type == "consistency_evaluate"
    assert payload["project_id"] == "prj_chain"
    assert payload["source_phase"] == "descubrimiento"
    assert len(payload["changes"]) == 1
