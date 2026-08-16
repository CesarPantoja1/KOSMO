from __future__ import annotations

from dataclasses import dataclass

import structlog

from kosmo.application.consistency.trigger_downstream import trigger_downstream_evaluation
from kosmo.contracts.persistence import OutboxPort
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import (
    FeatureNotFoundError,
    ProjectNotFoundError,
    RequirementsNotFoundError,
)
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)

_log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DeleteRequirementsInput:
    project_id: ProjectId
    feature_id: FeatureId


class DeleteRequirementsUseCase:
    """Caso de uso: elimina los requisitos EARS de una característica.

    El modelo de actividad derivado de los requisitos se elimina en cascada
    si existe.
    """

    def __init__(
        self,
        project_repo: ProjectRepository,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        diagram_repo: ActivityDiagramRepository,
        outbox: OutboxPort | None = None,
    ) -> None:
        self._project_repo = project_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._diagram_repo = diagram_repo
        self._outbox = outbox

    async def execute(self, input_data: DeleteRequirementsInput) -> None:
        instance = f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements"

        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=instance,
            )

        feature = await self._feature_repo.by_id(input_data.feature_id)
        if feature is None or feature.project_id != input_data.project_id:
            raise FeatureNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=instance,
            )

        markdown = await self._requirement_repo.by_feature_id(input_data.feature_id)
        if not markdown or not markdown.strip():
            raise RequirementsNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=instance,
            )

        await self._requirement_repo.delete(input_data.feature_id)
        await self._diagram_repo.delete(input_data.feature_id)

        await trigger_downstream_evaluation(
            self._outbox,
            project_id=input_data.project_id,
            source_phase=SpecPhase.REQUISITOS,
            changes=[
                {
                    "section": f"Requisitos de {feature.display_id}",
                    "description": "Eliminación de los requisitos",
                    "before": "",
                    "after": "",
                }
            ],
        )

        _log.info(
            "delete_requirements.success",
            project_id=str(input_data.project_id),
            feature_id=str(input_data.feature_id),
            display_id=feature.display_id,
        )
