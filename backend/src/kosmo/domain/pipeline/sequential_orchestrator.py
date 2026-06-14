from __future__ import annotations

from kosmo.contracts.pipeline.phase_errors import PhaseTransitionError
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import (
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
)

_PHASE_ORDER: list[SpecPhase] = [
    SpecPhase.DESCUBRIMIENTO,
    SpecPhase.CARACTERISTICAS,
    SpecPhase.REQUISITOS,
]


class SequentialOrchestrator:
    def __init__(
        self,
        document_repo: DocumentRepository,
        feature_repo: FeatureRepository,
        project_repo: ProjectRepository,
    ) -> None:
        self._document_repo = document_repo
        self._feature_repo = feature_repo
        self._project_repo = project_repo

    async def validate_transition(
        self,
        project_id: ProjectId,
        target_phase: SpecPhase,
    ) -> None:
        project = await self._project_repo.by_id(project_id)
        if project is None:
            raise PhaseTransitionError(
                detail="Proyecto no encontrado",
                instance="/pipeline/advance",
            )

        current_idx = _PHASE_ORDER.index(project.current_phase)
        target_idx = _PHASE_ORDER.index(target_phase)

        if target_idx <= current_idx and target_phase != project.current_phase:
            raise PhaseTransitionError(
                detail=(
                    f"No se puede retroceder de {project.current_phase.value}"
                    f" a {target_phase.value}"
                ),
                instance="/pipeline/advance",
            )

        if target_phase == SpecPhase.CARACTERISTICAS:
            doc = await self._document_repo.get_discovery(project_id)
            if doc is None:
                raise PhaseTransitionError(
                    detail=(
                        "No se puede avanzar a Caracteristicas sin un documento de discovery valido"
                    ),
                    instance="/pipeline/advance",
                )

        if target_phase == SpecPhase.REQUISITOS:
            features = await self._feature_repo.list_by_project(project_id)
            if not features:
                raise PhaseTransitionError(
                    detail="No se puede avanzar a Requisitos sin al menos una feature",
                    instance="/pipeline/advance",
                )

        project = await self._project_repo.update_phase(project_id, target_phase)
        if project is None:
            raise PhaseTransitionError(
                detail="No se pudo actualizar la fase del proyecto",
                instance="/pipeline/advance",
            )
