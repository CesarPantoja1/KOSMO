import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.features.create_characteristic import (
    CreateCharacteristicUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.pipeline.phase_outputs import SuggestFeaturesOutput
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.infrastructure.api.routers.features import (
    create_characteristic_manual,
)
from kosmo.infrastructure.api.schemas import (
    CreateCharacteristicRequest,
    FeatureResponse,
)


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


class MockSuggestFeaturesUseCase:
    async def execute(self, _input_data: Any) -> SuggestFeaturesOutput:
        return SuggestFeaturesOutput(suggestions=[], excluded_titles=[], domain_inferred="")


def _principal() -> Principal:
    return Principal(subject="usr_test123", scopes=frozenset({"*"}))


@pytest.mark.asyncio
async def test_create_manual_returns_201_and_feature_response() -> None:
    # Arrange
    repository: Any = InMemoryFeatureRepository()
    suggest_use_case: Any = MockSuggestFeaturesUseCase()
    use_case = CreateCharacteristicUseCase(feature_repo=repository, suggest_use_case=suggest_use_case)
    payload = CreateCharacteristicRequest(
        title="Catalogo de productos",
        description="Permite a los usuarios administrar el catalogo de productos del sistema",
    )

    # Act
    result = await create_characteristic_manual(
        project_id="prj_manual_test",
        payload=payload,
        _principal=_principal(),
        use_case=use_case,
    )

    # Assert
    assert isinstance(result, FeatureResponse)
    assert result.project_id == "prj_manual_test"
    assert result.title == "Catalogo de productos"
    assert result.number == 1
    assert result.display_id == "C01"
    assert result.id.startswith("feat_")
    assert result.slug == "catalogo-de-productos"
