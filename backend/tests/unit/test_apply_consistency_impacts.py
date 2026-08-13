from __future__ import annotations

import pytest

from kosmo.application.consistency.apply_consistency_impacts import ApplyConsistencyImpactsUseCase
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from kosmo.domain.sdd.document_converters import document_to_markdown, markdown_to_document
from tests.unit.fakes import (
    InMemoryActivityDiagramRepository,
    InMemoryDocumentRepository,
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
    InMemoryRequirementRepository,
    InMemoryTraceabilityRepository,
    InMemoryUnitOfWork,
)

_DEFAULT_MARKDOWN = "## Visión\n\nContenido de visión.\n\n## Alcance\n\nContenido de alcance original."


def _make_project(project_id: str = "prj_test") -> Project:
    return Project(
        id=ProjectId(project_id),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_test"),
    )


def _make_feature(project_id: ProjectId, feature_id: str = "feat_01") -> Feature:
    return Feature(
        id=FeatureId(feature_id),
        project_id=project_id,
        number=1,
        title="Test Feature",
        slug="test-feature",
        description="Descripción original.",
    )


def _make_uc(
    project_repo: InMemoryProjectRepository,
    document_repo: InMemoryDocumentRepository,
    *,
    feature_repo: InMemoryFeatureRepository | None = None,
    requirement_repo: InMemoryRequirementRepository | None = None,
    diagram_repo: InMemoryActivityDiagramRepository | None = None,
    traceability: InMemoryTraceabilityRepository | None = None,
) -> ApplyConsistencyImpactsUseCase:
    uow = InMemoryUnitOfWork(
        projects=project_repo,
        documents=document_repo,
        features=feature_repo,
        requirements=requirement_repo,
        diagrams=diagram_repo,
        traceability=traceability,
    )
    return ApplyConsistencyImpactsUseCase(uow=uow)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_discovery_document_update_applies_diff() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    document_repo = InMemoryDocumentRepository()
    document_repo.discovery_docs[str(project.id)] = markdown_to_document(_DEFAULT_MARKDOWN)
    uc = _make_uc(project_repo, document_repo)

    # Act
    result = await uc.execute(
        project_id=project.id,
        impacts=[
            {
                "artifact_type": "DiscoveryDocument",
                "target_id": str(project.id),
                "action": "update",
                "field": "content",
                "before": "Contenido de alcance original.",
                "after": "Contenido de alcance actualizado.",
            }
        ],
    )

    # Assert
    assert len(result.applied) == 1
    assert len(result.failed) == 0

    doc = await document_repo.get_discovery(project.id)
    assert doc is not None
    markdown = document_to_markdown(doc)
    assert "Contenido de alcance actualizado." in markdown
    assert "Contenido de alcance original." not in markdown


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_discovery_document_delete_is_rejected() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    document_repo = InMemoryDocumentRepository()
    document_repo.discovery_docs[str(project.id)] = markdown_to_document(_DEFAULT_MARKDOWN)
    uc = _make_uc(project_repo, document_repo)

    # Act
    result = await uc.execute(
        project_id=project.id,
        impacts=[
            {
                "artifact_type": "DiscoveryDocument",
                "target_id": str(project.id),
                "action": "delete",
                "field": "",
                "before": "",
                "after": "",
            }
        ],
    )

    # Assert: el documento no puede eliminarse
    assert len(result.applied) == 0
    assert len(result.failed) == 1
    assert "no puede eliminarse" in result.failed[0].reason


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_unknown_artifact_type_is_failed() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    document_repo = InMemoryDocumentRepository()
    uc = _make_uc(project_repo, document_repo)

    # Act
    result = await uc.execute(
        project_id=project.id,
        impacts=[
            {
                "artifact_type": "ArtefactoInexistente",
                "target_id": "feat_01",
                "action": "update",
                "field": "description",
                "before": "a",
                "after": "b",
            }
        ],
    )

    # Assert
    assert len(result.applied) == 0
    assert len(result.failed) == 1
    assert "desconocido" in result.failed[0].reason


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_requirement_update_rebuilds_traceability_edges() -> None:
    # Arrange: requisitos existentes y un edge viejo que debe reemplazarse
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    document_repo = InMemoryDocumentRepository()
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(_make_feature(project.id))
    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(
        FeatureId("feat_01"),
        "### REQ-1.1 Procesamiento de pagos\n\nEl sistema debe procesar pagos.\n",
    )
    traceability = InMemoryTraceabilityRepository()
    await traceability.add_edge("feature", "feat_01", "requirement", "req_viejo")
    uc = _make_uc(
        project_repo,
        document_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        traceability=traceability,
    )

    # Act
    result = await uc.execute(
        project_id=project.id,
        impacts=[
            {
                "artifact_type": "EARSRequirement",
                "target_id": "feat_01",
                "action": "update",
                "field": "content",
                "before": "El sistema debe procesar pagos.",
                "after": "El sistema debe procesar pagos con tarjeta.",
            }
        ],
    )

    # Assert: requisitos actualizados y edges reemplazados en la misma transaccion
    assert len(result.applied) == 1
    assert len(result.failed) == 0
    saved = await requirement_repo.by_feature_id(FeatureId("feat_01"))
    assert saved is not None
    assert "con tarjeta" in saved

    assert len(traceability.edges) == 1
    assert traceability.edges[0][1] == "feat_01"
    assert traceability.edges[0][3].startswith("req_")
    assert traceability.edges[0][3] != "req_viejo"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_failed_impact_does_not_block_subsequent_impacts() -> None:
    # Arrange: primer impacto invalido, segundo valido
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    document_repo = InMemoryDocumentRepository()
    document_repo.discovery_docs[str(project.id)] = markdown_to_document(_DEFAULT_MARKDOWN)
    uc = _make_uc(project_repo, document_repo)

    # Act
    result = await uc.execute(
        project_id=project.id,
        impacts=[
            {
                "artifact_type": "DiscoveryDocument",
                "target_id": str(project.id),
                "action": "update",
                "field": "content",
                "before": "Texto que no existe",
                "after": "No importa",
            },
            {
                "artifact_type": "DiscoveryDocument",
                "target_id": str(project.id),
                "action": "update",
                "field": "content",
                "before": "Contenido de alcance original.",
                "after": "Contenido de alcance actualizado.",
            },
        ],
    )

    # Assert: el fallo del primero no envenena la transaccion del segundo
    assert len(result.applied) == 1
    assert len(result.failed) == 1
    doc = await document_repo.get_discovery(project.id)
    assert doc is not None
    assert "Contenido de alcance actualizado." in document_to_markdown(doc)
