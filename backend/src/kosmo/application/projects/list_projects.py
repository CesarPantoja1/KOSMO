from __future__ import annotations

from kosmo.contracts.sdd.ids import UserId
from kosmo.contracts.sdd.project import Project
from kosmo.contracts.sdd.repositories import ProjectRepository


class ListProjectsUseCase:
    def __init__(self, project_repository: ProjectRepository) -> None:
        self._project_repository = project_repository

    async def execute(self, owner_id: UserId) -> list[Project]:
        return await self._project_repository.list_by_owner(str(owner_id))
