from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.errors import DiagramNotFoundError, FeatureNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    FeatureRepository,
)


@dataclass(frozen=True)
class GetDiagramInput:
    project_id: ProjectId
    feature_id: FeatureId


@dataclass(frozen=True)
class GetDiagramOutput:
    diagram: DiagramaActividad


class GetActivityDiagramUseCase:
    def __init__(
        self,
        feature_repo: FeatureRepository,
        diagram_repo: ActivityDiagramRepository,
    ) -> None:
        self._feature_repo = feature_repo
        self._diagram_repo = diagram_repo

    async def execute(self, input_data: GetDiagramInput) -> GetDiagramOutput:
        feature = await self._feature_repo.by_id(input_data.feature_id)
        if feature is None or feature.project_id != input_data.project_id:
            raise FeatureNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/diagram",
            )

        diagram = await self._diagram_repo.by_feature_id(input_data.feature_id)
        if diagram is None:
            raise DiagramNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/diagram",
            )

        return GetDiagramOutput(diagram=diagram)
