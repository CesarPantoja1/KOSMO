from typing import Any

import pytest

from kosmo.application.features.create_characteristic import (
    CreateCharacteristicUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.pipeline.phase_outputs import SuggestFeaturesOutput
from kosmo.infrastructure.api.routers.features import (
    create_characteristic_manual,
)
from kosmo.infrastructure.api.schemas import (
    CreateCharacteristicRequest,
    FeatureResponse,
)
from tests.unit.fakes import InMemoryFeatureRepository


class MockSuggestFeaturesUseCase:
    async def execute(self, _input_data: Any) -> SuggestFeaturesOutput:
        return SuggestFeaturesOutput(suggestions=[], excluded_titles=[], domain_inferred="")


def _principal() -> Principal:
    return Principal(subject="usr_test123", scopes=frozenset({"*"}))


@pytest.mark.asyncio
@pytest.mark.unit
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
