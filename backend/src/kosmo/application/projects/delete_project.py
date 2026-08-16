from __future__ import annotations

from dataclasses import dataclass

import structlog

from kosmo.contracts.agent_memory import AgentMemoryPort
from kosmo.contracts.chat import ChatRepository
from kosmo.contracts.consistency import (
    ConsistencyEvaluationRepository,
    TraceabilityRepository,
)
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)

_log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DeleteProjectInput:
    project_id: ProjectId
    owner_id: UserId


class DeleteProjectUseCase:
    """Caso de uso: elimina un proyecto y todos sus artefactos en cascada.

    Descubrimiento, versiones, características, requisitos, modelos, chat,
    evaluaciones de consistencia, sesiones de agente y trazabilidad.
    """

    def __init__(
        self,
        project_repo: ProjectRepository,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        diagram_repo: ActivityDiagramRepository,
        document_repo: DocumentRepository,
        chat_repo: ChatRepository,
        consistency_evaluation_repo: ConsistencyEvaluationRepository,
        traceability_repo: TraceabilityRepository | None = None,
        agent_memory: AgentMemoryPort | None = None,
    ) -> None:
        self._project_repo = project_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._diagram_repo = diagram_repo
        self._document_repo = document_repo
        self._chat_repo = chat_repo
        self._consistency_evaluation_repo = consistency_evaluation_repo
        self._traceability_repo = traceability_repo
        self._agent_memory = agent_memory

    async def execute(self, input_data: DeleteProjectInput) -> None:
        project = await self._project_repo.by_id(input_data.project_id)
        if project is None or str(project.owner_id) != str(input_data.owner_id):
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}",
            )

        features = await self._feature_repo.list_by_project(input_data.project_id)
        for feature in features:
            await self._requirement_repo.delete(feature.id)
            await self._diagram_repo.delete(feature.id)
            await self._delete_traceability(str(feature.id))
            await self._feature_repo.delete(feature.id)

        await self._delete_traceability(str(input_data.project_id))

        await self._document_repo.delete_discovery(input_data.project_id)
        await self._document_repo.delete_versions_by_project(input_data.project_id)
        await self._chat_repo.delete_by_project(input_data.project_id)
        await self._consistency_evaluation_repo.delete_by_project(input_data.project_id)

        if self._agent_memory is not None:
            await self._agent_memory.delete_by_project(input_data.project_id)

        await self._project_repo.delete(input_data.project_id)

        _log.info(
            "delete_project.success",
            project_id=str(input_data.project_id),
            feature_count=len(features),
        )

    async def _delete_traceability(self, entity_id: str) -> None:
        if self._traceability_repo is None:
            return
        try:
            await self._traceability_repo.delete_by_entity_id(entity_id)
        except Exception:
            _log.warning(
                "delete_project.traceability_cleanup_failed",
                entity_id=entity_id,
                exc_info=True,
            )
