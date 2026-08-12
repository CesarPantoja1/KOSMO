from __future__ import annotations

import pytest

from kosmo.application.consistency.apply_consistency_impacts import ApplyConsistencyImpactsUseCase
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from kosmo.domain.sdd.document_converters import document_to_markdown, markdown_to_document
from tests.unit.fakes import (
    InMemoryActivityDiagramRepository,
    InMemoryDocumentRepository,
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
    InMemoryRequirementRepository,
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


def _make_uc(
    project_repo: InMemoryProjectRepository,
    document_repo: InMemoryDocumentRepository,
) -> ApplyConsistencyImpactsUseCase:
    return ApplyConsistencyImpactsUseCase(
        project_repo=project_repo,
        feature_repo=InMemoryFeatureRepository(),
        requirement_repo=InMemoryRequirementRepository(),
        diagram_repo=InMemoryActivityDiagramRepository(),
        document_repo=document_repo,
    )


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
