from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.project import Project
from kosmo.contracts.sdd.repositories import ProjectRepository


class GetProjectUseCase:
    def __init__(self, project_repo: ProjectRepository) -> None:
        self._project_repo = project_repo

    async def execute(self, project_id: ProjectId) -> Project:
        project = await self._project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(str(project_id))
        return project
