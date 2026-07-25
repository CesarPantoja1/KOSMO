from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kosmo.application.modelo.get_diagram import (
    GetActivityDiagramUseCase,
    GetDiagramInput,
    GetDiagramOutput,
)
from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.errors import (
    DiagramNotFoundError,
    FeatureNotFoundError,
)
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId, ProjectId


class InMemoryFeatureRepository:
    def __init__(self) -> None:
        self.features: dict[str, Feature] = {}

    async def by_id(self, feature_id: FeatureId) -> Feature | None:
        return self.features.get(str(feature_id))

    async def list_by_project(self, project_id: ProjectId) -> list[Feature]:
        return [f for f in self.features.values() if str(f.project_id) == str(project_id)]

    async def save(self, feature: Feature) -> Feature:
        self.features[str(feature.id)] = feature
        return feature

    async def save_many(self, features: list[Feature]) -> list[Feature]:
        for f in features:
            self.features[str(f.id)] = f
        return features

    async def next_number(self, project_id: ProjectId) -> int:  # noqa: ARG002
        return 1


class InMemoryActivityDiagramRepository:
    def __init__(self) -> None:
        self._diagrams: dict[str, DiagramaActividad] = {}

    async def save(self, diagram: DiagramaActividad) -> DiagramaActividad:
        self._diagrams[str(diagram.feature_id)] = diagram
        return diagram

    async def by_feature_id(self, feature_id: FeatureId) -> DiagramaActividad | None:
        return self._diagrams.get(str(feature_id))

    async def exists(self, feature_id: FeatureId) -> bool:
        return str(feature_id) in self._diagrams


def _make_feature(feature_id: str = "feat_01", project_id: str = "prj_01") -> Feature:
    return Feature(
        id=FeatureId(feature_id),
        number=1,
        title="Test Feature",
        slug="test-feature",
        description="Test feature description",
        project_id=ProjectId(project_id),
    )


def _make_diagram(feature_id: str = "feat_01") -> DiagramaActividad:
    now = datetime.now(UTC)
    return DiagramaActividad(
        id=ActivityDiagramId("dia_01"),
        feature_id=FeatureId(feature_id),
        diagram_syntax="@startuml\nstart\nstop\n@enduml",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_diagram_returns_diagram_when_exists() -> None:
    # Arrange
    feature = _make_feature()
    diagram = _make_diagram()

    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature)

    diagram_repo = InMemoryActivityDiagramRepository()
    await diagram_repo.save(diagram)

    uc = GetActivityDiagramUseCase(
        feature_repo=feature_repo,
        diagram_repo=diagram_repo,
    )

    # Act
    output = await uc.execute(
        GetDiagramInput(
            project_id=ProjectId("prj_01"),
            feature_id=FeatureId("feat_01"),
        )
    )

    # Assert
    assert isinstance(output, GetDiagramOutput)
    assert str(output.diagram.id) == "dia_01"
    assert str(output.diagram.feature_id) == "feat_01"
    assert output.diagram.diagram_syntax == "@startuml\nstart\nstop\n@enduml"


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_diagram_raises_when_feature_not_found() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    diagram_repo = InMemoryActivityDiagramRepository()

    uc = GetActivityDiagramUseCase(
        feature_repo=feature_repo,
        diagram_repo=diagram_repo,
    )

    # Act & Assert
    with pytest.raises(FeatureNotFoundError):
        await uc.execute(
            GetDiagramInput(
                project_id=ProjectId("prj_01"),
                feature_id=FeatureId("feat_missing"),
            )
        )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_diagram_raises_when_no_diagram_for_feature() -> None:
    # Arrange
    feature = _make_feature()

    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature)

    diagram_repo = InMemoryActivityDiagramRepository()

    uc = GetActivityDiagramUseCase(
        feature_repo=feature_repo,
        diagram_repo=diagram_repo,
    )

    # Act & Assert
    with pytest.raises(DiagramNotFoundError):
        await uc.execute(
            GetDiagramInput(
                project_id=ProjectId("prj_01"),
                feature_id=FeatureId("feat_01"),
            )
        )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_diagram_raises_when_feature_belongs_to_wrong_project() -> None:
    # Arrange
    feature = _make_feature(feature_id="feat_01", project_id="prj_02")

    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature)

    diagram_repo = InMemoryActivityDiagramRepository()

    uc = GetActivityDiagramUseCase(
        feature_repo=feature_repo,
        diagram_repo=diagram_repo,
    )

    # Act & Assert
    with pytest.raises(FeatureNotFoundError):
        await uc.execute(
            GetDiagramInput(
                project_id=ProjectId("prj_01"),
                feature_id=FeatureId("feat_01"),
            )
        )
