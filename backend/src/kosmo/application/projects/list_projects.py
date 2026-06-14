from __future__ import annotations

from kosmo.contracts.sdd.project import Project
from kosmo.contracts.sdd.repositories import ProjectRepository


class ListProjectsUseCase:
    def __init__(self, project_repo: ProjectRepository) -> None:
        self._project_repo = project_repo

    async def execute(self, owner_id: str) -> list[Project]:
        return await self._project_repo.list_by_owner(owner_id)
