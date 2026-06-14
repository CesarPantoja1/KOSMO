from __future__ import annotations

from kosmo.contracts.pipeline.pipeline_ports import PipelineRepository
from kosmo.contracts.pipeline.pipeline_state import KOSMOPipelineState
from kosmo.contracts.sdd.document import ProjectPhase, ProjectStatus
from kosmo.contracts.sdd.ids import PipelineId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from kosmo.contracts.sdd.repositories import ProjectRepository
from kosmo.domain.sdd.id_generator import IdGenerator


class CreateProjectUseCase:
    def __init__(self, project_repo: ProjectRepository, pipeline_repo: PipelineRepository) -> None:
        self._project_repo = project_repo
        self._pipeline_repo = pipeline_repo

    async def execute(
        self,
        name: str,
        description: str,
        owner_id: str,
    ) -> Project:
        project = Project(
            id=ProjectId(IdGenerator.generate("project")),
            name=name,
            description=description,
            owner_id=owner_id,
            current_phase=ProjectPhase.descubrimiento,
            status=ProjectStatus.en_proceso,
        )
        created = await self._project_repo.save(project)

        state = KOSMOPipelineState(
            project_id=created.id,
            user_id=UserId(owner_id),
            pipeline_id=PipelineId(IdGenerator.generate("pipeline")),
        )
        await self._pipeline_repo.save(state)

        return created
