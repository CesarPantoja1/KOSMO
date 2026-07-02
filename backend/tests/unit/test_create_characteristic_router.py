import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.features.create_characteristic import (
    CreateCharacteristicUseCase,
)
from kosmo.contracts.auth import Principal
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


def _principal() -> Principal:
    return Principal(subject="usr_test123", scopes=frozenset({"*"}))


@pytest.mark.asyncio
async def test_create_manual_returns_201_and_feature_response() -> None:
    # Arrange
    repository: Any = InMemoryFeatureRepository()
    use_case = CreateCharacteristicUseCase(feature_repo=repository)
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


@pytest.mark.asyncio
async def test_create_manual_whitespace_title_returns_400() -> None:
    # Arrange
    repository: Any = InMemoryFeatureRepository()
    use_case = CreateCharacteristicUseCase(feature_repo=repository)
    payload = CreateCharacteristicRequest(
        title="   ",
        description="Descripcion valida",
    )

    # Act & Assert
    with pytest.raises(Exception, match="vacio"):
        await create_characteristic_manual(
            project_id="prj_whitespace",
            payload=payload,
            _principal=_principal(),
            use_case=use_case,
        )


@pytest.mark.asyncio
async def test_create_manual_title_at_max_50_chars_succeeds() -> None:
    # Arrange
    repository: Any = InMemoryFeatureRepository()
    use_case = CreateCharacteristicUseCase(feature_repo=repository)
    payload = CreateCharacteristicRequest(
        title="A" * 50,
        description="Descripcion valida",
    )

    # Act
    result = await create_characteristic_manual(
        project_id="prj_max_title",
        payload=payload,
        _principal=_principal(),
        use_case=use_case,
    )

    # Assert
    assert isinstance(result, FeatureResponse)
    assert len(result.title) == 50
    assert result.number == 1
    assert result.display_id == "C01"


@pytest.mark.asyncio
async def test_create_manual_description_at_max_500_chars_succeeds() -> None:
    # Arrange
    repository: Any = InMemoryFeatureRepository()
    use_case = CreateCharacteristicUseCase(feature_repo=repository)
    payload = CreateCharacteristicRequest(
        title="Titulo valido",
        description="D" * 500,
    )

    # Act
    result = await create_characteristic_manual(
        project_id="prj_max_desc",
        payload=payload,
        _principal=_principal(),
        use_case=use_case,
    )

    # Assert
    assert isinstance(result, FeatureResponse)
    assert len(result.description) == 500
    assert result.number == 1
    assert result.display_id == "C01"


@pytest.mark.asyncio
async def test_create_manual_increments_number_for_subsequent_creations() -> None:
    # Arrange
    repository: Any = InMemoryFeatureRepository()
    use_case = CreateCharacteristicUseCase(feature_repo=repository)
    project_id = "prj_multi"

    first_payload = CreateCharacteristicRequest(
        title="Feature A",
        description="Primera caracteristica",
    )

    # Act
    first = await create_characteristic_manual(
        project_id=project_id,
        payload=first_payload,
        _principal=_principal(),
        use_case=use_case,
    )

    second_payload = CreateCharacteristicRequest(
        title="Feature B",
        description="Segunda caracteristica",
    )
    second = await create_characteristic_manual(
        project_id=project_id,
        payload=second_payload,
        _principal=_principal(),
        use_case=use_case,
    )

    third_payload = CreateCharacteristicRequest(
        title="Feature C",
        description="Tercera caracteristica",
    )
    third = await create_characteristic_manual(
        project_id=project_id,
        payload=third_payload,
        _principal=_principal(),
        use_case=use_case,
    )

    # Assert
    assert first.number == 1
    assert first.display_id == "C01"
    assert second.number == 2
    assert second.display_id == "C02"
    assert third.number == 3
    assert third.display_id == "C03"
    assert first.id != second.id != third.id
