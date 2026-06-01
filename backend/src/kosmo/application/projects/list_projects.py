from kosmo.contracts.sdd.project import Project
from kosmo.contracts.sdd.repositories import ProjectRepository


class ListProjectsUseCase:
    def __init__(self, project_repo: ProjectRepository) -> None:
        self._project_repo = project_repo

    async def execute(self) -> list[Project]:
        return await self._project_repo.list_all()
