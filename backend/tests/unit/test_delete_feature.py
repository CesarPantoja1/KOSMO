from __future__ import annotations

import pytest

from kosmo.application.features.delete_feature import DeleteFeatureUseCase
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from tests.unit.fakes import (
    InMemoryFeatureRepository,
    InMemoryOutbox,
    InMemoryProjectRepository,
    InMemoryTraceabilityRepository,
)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_feature_enqueues_downstream_evaluation() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    project = Project(
        id=ProjectId("prj_del"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_01"),
    )
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    feature = Feature(
        id=FeatureId("feat_del"),
        number=1,
        title="Característica a eliminar",
        slug="caracteristica-a-eliminar",
        description="Descripción",
        project_id=project.id,
    )
    await feature_repo.save(feature)

    outbox = InMemoryOutbox()
    use_case = DeleteFeatureUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        traceability_repo=InMemoryTraceabilityRepository(),
        outbox=outbox,
    )

    # Act
    await use_case.execute(project.id, feature.id)

    # Assert — eliminar una característica dispara la verificación de las fases a la derecha
    assert await feature_repo.by_id(feature.id) is None
    assert len(outbox.jobs) == 1
    job_type, payload = outbox.jobs[0]
    assert job_type == "consistency_evaluate"
    assert payload["project_id"] == "prj_del"
    assert payload["source_phase"] == "caracteristicas"
    assert payload["changes"][0]["after"] == ""


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_feature_without_outbox_keeps_working() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    project = Project(
        id=ProjectId("prj_del2"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_01"),
    )
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    feature = Feature(
        id=FeatureId("feat_del2"),
        number=1,
        title="Otra característica",
        slug="otra-caracteristica",
        description="Descripción",
        project_id=project.id,
    )
    await feature_repo.save(feature)

    use_case = DeleteFeatureUseCase(project_repo=project_repo, feature_repo=feature_repo)

    # Act & Assert — sin outbox el caso de uso sigue funcionando
    await use_case.execute(project.id, feature.id)
    assert await feature_repo.by_id(feature.id) is None
