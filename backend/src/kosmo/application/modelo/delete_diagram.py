from __future__ import annotations

from dataclasses import dataclass

import structlog

from kosmo.contracts.sdd.errors import DiagramNotFoundError, FeatureNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    FeatureRepository,
)

_log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DeleteDiagramInput:
    project_id: ProjectId
    feature_id: FeatureId


class DeleteActivityDiagramUseCase:
    """Caso de uso: elimina el diagrama de actividad (modelo) de una característica."""

    def __init__(
        self,
        feature_repo: FeatureRepository,
        diagram_repo: ActivityDiagramRepository,
    ) -> None:
        self._feature_repo = feature_repo
        self._diagram_repo = diagram_repo

    async def execute(self, input_data: DeleteDiagramInput) -> None:
        instance = f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/diagram"

        feature = await self._feature_repo.by_id(input_data.feature_id)
        if feature is None or feature.project_id != input_data.project_id:
            raise FeatureNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=instance,
            )

        diagram = await self._diagram_repo.by_feature_id(input_data.feature_id)
        if diagram is None:
            raise DiagramNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=instance,
            )

        await self._diagram_repo.delete(input_data.feature_id)

        _log.info(
            "delete_diagram.success",
            project_id=str(input_data.project_id),
            feature_id=str(input_data.feature_id),
        )
