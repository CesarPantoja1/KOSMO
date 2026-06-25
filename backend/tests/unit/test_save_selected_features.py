import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.features.save_features import (
    SaveSelectedFeaturesInput,
    SaveSelectedFeaturesOutput,
    SaveSelectedFeaturesUseCase,
)
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId


class InMemoryFeatureRepository:
    def __init__(self) -> None:
        self.features: dict[str, Feature] = {}

    async def by_id(self, feature_id: FeatureId) -> Feature | None:
        return self.features.get(str(feature_id))

    async def list_by_project(self, project_id: ProjectId) -> list[Feature]:
        return [f for f in self.features.values() if str(f.project_id) == str(project_id)]

    async def save(self, feature: Feature) -> Feature:  # type: ignore[override]
        self.features[str(feature.id)] = feature
        return feature

    async def save_many(self, features: list[Feature]) -> list[Feature]:
        for f in features:
            self.features[str(f.id)] = f
        return features

    async def next_number(self, project_id: ProjectId) -> int:
        project_features = await self.list_by_project(project_id)
        return max((f.number for f in project_features), default=0) + 1


@pytest.mark.asyncio
async def test_save_selected_features_saves_with_correct_numbering() -> None:
    # Arrange
    repository: Any = InMemoryFeatureRepository()
    use_case = SaveSelectedFeaturesUseCase(feature_repo=repository)
    project_id = ProjectId("prj_feat123")

    input_data = SaveSelectedFeaturesInput(
        project_id=project_id,
        features=[
            {"title": "Feature A", "description": "Desc A"},
            {"title": "Feature B", "description": "Desc B"},
        ],
    )

    # Act
    result = await use_case.execute(input_data)

    # Assert
    assert isinstance(result, SaveSelectedFeaturesOutput)
    assert len(result.features) == 2
    assert result.features[0].number == 1
    assert result.features[1].number == 2
    assert result.features[0].title == "Feature A"
    assert result.features[1].title == "Feature B"


@pytest.mark.asyncio
async def test_save_selected_features_assigns_project_id() -> None:
    # Arrange
    repository: Any = InMemoryFeatureRepository()
    use_case = SaveSelectedFeaturesUseCase(feature_repo=repository)
    project_id = ProjectId("prj_proj456")

    input_data = SaveSelectedFeaturesInput(
        project_id=project_id,
        features=[
            {"title": "Nueva Feature", "description": "Descripción"},
        ],
    )

    # Act
    result = await use_case.execute(input_data)

    # Assert
    assert len(result.features) == 1
    assert result.features[0].project_id == project_id
    assert str(result.features[0].id).startswith("feat_")


@pytest.mark.asyncio
async def test_save_selected_features_returns_saved_features() -> None:
    # Arrange
    repository: Any = InMemoryFeatureRepository()
    use_case = SaveSelectedFeaturesUseCase(feature_repo=repository)
    project_id = ProjectId("prj_return789")

    input_data = SaveSelectedFeaturesInput(
        project_id=project_id,
        features=[
            {
                "title": "Feature Persistida",
                "description": "Descripción persistida",
                "rationale": "Justificación",
                "inferred_from": ["src/doc.md"],
            },
        ],
    )

    # Act
    result = await use_case.execute(input_data)

    # Assert
    saved = await repository.by_id(result.features[0].id)
    assert saved is not None
    assert saved.title == "Feature Persistida"
    assert saved.description == "Descripción persistida"
    assert saved.rationale == "Justificación"


@pytest.mark.asyncio
async def test_save_selected_features_strips_identifier_prefix() -> None:
    # Arrange
    repository: Any = InMemoryFeatureRepository()
    use_case = SaveSelectedFeaturesUseCase(feature_repo=repository)
    project_id = ProjectId("prj_strip456")

    input_data = SaveSelectedFeaturesInput(
        project_id=project_id,
        features=[
            {"title": "C03 Feature Limpia", "description": "Desc"},
        ],
    )

    # Act
    result = await use_case.execute(input_data)

    # Assert
    assert result.features[0].title == "Feature Limpia"
    assert result.features[0].slug == "feature-limpia"
