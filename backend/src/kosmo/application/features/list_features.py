from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository


@dataclass(frozen=True)
class ListFeaturesInput:
    project_id: ProjectId


@dataclass(frozen=True)
class ListFeaturesOutput:
    features: list[Feature]


class ListFeaturesUseCase:
    def __init__(self, feature_repo: FeatureRepository) -> None:
        self._feature_repo = feature_repo

    async def execute(self, input_data: ListFeaturesInput) -> ListFeaturesOutput:
        features = await self._feature_repo.list_by_project(input_data.project_id)
        return ListFeaturesOutput(features=features)
