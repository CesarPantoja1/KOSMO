from __future__ import annotations

from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import (
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)


class SaveRequirementsUseCase:
    """Caso de uso: guarda o actualiza los requisitos EARS en formato Markdown."""

    def __init__(
        self,
        project_repo: ProjectRepository,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
    ) -> None:
        self._project_repo = project_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo

    async def execute(self, project_id: ProjectId, feature_id: FeatureId, markdown: str) -> None:
        from kosmo.contracts.sdd.errors import ProjectNotFoundError, FeatureNotFoundError

        project = await self._project_repo.by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(project_id),
                instance=f"/api/v1/projects/{project_id}/features/{feature_id}/requirements",
            )

        feature = await self._feature_repo.by_id(feature_id)
        if feature is None or feature.project_id != project_id:
            raise FeatureNotFoundError(
                feature_id=str(feature_id),
                instance=f"/api/v1/projects/{project_id}/features/{feature_id}/requirements",
            )

        await self._requirement_repo.save(feature_id, markdown)
