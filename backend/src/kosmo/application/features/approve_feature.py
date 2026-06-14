from __future__ import annotations

from kosmo.contracts.pipeline.pipeline_ports import PipelineRepository
from kosmo.contracts.sdd.document import FeatureStatus
from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.domain.features.status_transitions import transition_feature_status


class ApproveFeatureUseCase:
    def __init(self, pipeline_repo: PipelineRepository) -> None:
        self._pipeline_repo = pipeline_repo

    def __init__(self, pipeline_repo: PipelineRepository) -> None:
        self._pipeline_repo = pipeline_repo

    async def execute(
        self,
        project_id: ProjectId,
        feature_id: FeatureId,
    ) -> Feature:
        state = await self._pipeline_repo.get(project_id)
        if state is None:
            raise ValueError(f"No se encontro el pipeline para el proyecto {project_id}")

        feature = next(
            (f for f in state.features if f.id == feature_id),
            None,
        )
        if feature is None:
            raise FeatureNotFoundError(
                feature_id=feature_id,
                instance=f"/features/{feature_id}",
            )

        new_status = transition_feature_status(feature.status, FeatureStatus.aprobada, feature_id)
        updated_feature = Feature(
            id=feature.id,
            number=feature.number,
            title=feature.title,
            slug=feature.slug,
            description=feature.description,
            status=new_status,
            rationale=feature.rationale,
            inferred_from=feature.inferred_from,
            requirements_document=feature.requirements_document,
            created_at=feature.created_at,
        )

        state.features = [updated_feature if f.id == feature_id else f for f in state.features]
        await self._pipeline_repo.save(state)
        return updated_feature
