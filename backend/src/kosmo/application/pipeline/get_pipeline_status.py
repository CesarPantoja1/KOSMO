from __future__ import annotations

from kosmo.contracts.pipeline.pipeline_ports import PipelineRepository
from kosmo.contracts.pipeline.pipeline_state import KOSMOPipelineState
from kosmo.contracts.sdd.ids import ProjectId


class GetPipelineStatusUseCase:
    def __init__(self, pipeline_repo: PipelineRepository) -> None:
        self._pipeline_repo = pipeline_repo

    async def execute(self, project_id: ProjectId) -> KOSMOPipelineState | None:
        return await self._pipeline_repo.get(project_id)
