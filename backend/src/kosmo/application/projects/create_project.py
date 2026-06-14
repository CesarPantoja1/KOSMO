from __future__ import annotations

from kosmo.contracts.sdd.document import ProjectPhase, ProjectStatus
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.project import Project
from kosmo.contracts.sdd.repositories import ProjectRepository
from kosmo.domain.sdd.document_converters import slugify_spanish
from kosmo.domain.sdd.id_generator import IdGenerator


class CreateProjectUseCase:
    def __init__(self, project_repo: ProjectRepository) -> None:
        self._project_repo = project_repo

    async def execute(
        self,
        name: str,
        description: str,
        owner_id: str,
    ) -> Project:
        existing = await self._project_repo.list_by_owner(owner_id)
        existing_slugs = {p.slug for p in existing}

        base = slugify_spanish(name)
        slug = base
        counter = 2
        while slug in existing_slugs:
            slug = f"{base}-{counter}"
            counter += 1

        project = Project(
            id=ProjectId(IdGenerator.generate("project")),
            name=name,
            slug=slug,
            description=description,
            owner_id=owner_id,
            current_phase=ProjectPhase.descubrimiento,
            status=ProjectStatus.en_proceso,
        )
        return await self._project_repo.save(project)
