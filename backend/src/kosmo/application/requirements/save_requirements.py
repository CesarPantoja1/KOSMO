from __future__ import annotations

from kosmo.contracts.pipeline.pipeline_ports import PipelineRepository
from kosmo.contracts.pipeline.pipeline_state import KOSMOPipelineState
from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.contracts.sdd.ids import FeatureId, ProjectId


class SaveRequirementsUseCase:
    def __init__(self, pipeline_repo: PipelineRepository) -> None:
        self._pipeline_repo = pipeline_repo

    async def execute(
        self,
        project_id: ProjectId,
        feature_id: FeatureId,
        document: RichTextDocument,
    ) -> KOSMOPipelineState:
        state = await self._pipeline_repo.get(project_id)
        if state is None:
            raise ValueError(f"No se encontro el pipeline para el proyecto {project_id}")

        feature = next(
            (f for f in state.features if f.id == feature_id),
            None,
        )
        if feature is None:
            from kosmo.contracts.sdd.errors import FeatureNotFoundError

            raise FeatureNotFoundError(
                feature_id=feature_id,
                instance=f"/features/{feature_id}",
            )

        from kosmo.contracts.sdd.feature import Feature

        updated_feature = Feature(
            id=feature.id,
            number=feature.number,
            title=feature.title,
            slug=feature.slug,
            description=feature.description,
            status=feature.status,
            rationale=feature.rationale,
            inferred_from=feature.inferred_from,
            requirements_document=document,
            created_at=feature.created_at,
        )

        state.features = [updated_feature if f.id == feature_id else f for f in state.features]
        from datetime import UTC, datetime

        state.updated_at = datetime.now(UTC)
        state = await self._pipeline_repo.save(state)
        return state
