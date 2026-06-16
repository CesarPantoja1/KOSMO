from __future__ import annotations

from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.project import Project
from kosmo.contracts.sdd.repositories import ProjectRepository


class GetProjectUseCase:
    def __init__(self, project_repository: ProjectRepository) -> None:
        self._project_repository = project_repository

    async def execute(self, project_id: ProjectId) -> Project:
        project = await self._project_repository.by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(project_id),
                instance=f"/api/v1/projects/{project_id}",
            )
        return project
