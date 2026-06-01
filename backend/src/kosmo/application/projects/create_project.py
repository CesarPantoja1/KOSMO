from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.project import Project, ProjectPhase, ProjectStatus
from kosmo.contracts.sdd.repositories import ProjectRepository
from kosmo.domain.sdd.document_converters import slugify_spanish
from kosmo.domain.sdd.id_generator import IdGenerator


class CreateProjectUseCase:
    def __init__(self, project_repo: ProjectRepository) -> None:
        self._project_repo = project_repo

    async def execute(self, name: str, description: str) -> Project:
        slug = slugify_spanish(name, max_length=80)
        existing = await self._project_repo.get_by_slug(slug)
        if existing is not None:
            counter = 2
            while True:
                candidate = f"{slug}-{counter}"
                if await self._project_repo.get_by_slug(candidate) is None:
                    slug = candidate
                    break
                counter += 1

        project = Project(
            id=ProjectId(IdGenerator.generate("project")),
            name=name,
            slug=slug,
            description=description,
            current_phase=ProjectPhase.DESCUBRIMIENTO,
            status=ProjectStatus.EN_PROGRESO,
        )

        await self._project_repo.add(project)
        return project
