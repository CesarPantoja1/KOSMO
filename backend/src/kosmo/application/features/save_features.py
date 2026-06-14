from __future__ import annotations

from kosmo.contracts.pipeline.phase_outputs import SuggestedFeature
from kosmo.contracts.pipeline.pipeline_ports import PipelineRepository
from kosmo.contracts.sdd.document import FeatureStatus
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.sdd.id_generator import IdGenerator


class SaveSelectedFeaturesUseCase:
    def __init__(self, pipeline_repo: PipelineRepository) -> None:
        self._pipeline_repo = pipeline_repo

    async def execute(
        self,
        project_id: ProjectId,
        selected_suggestions: list[SuggestedFeature],
    ) -> list[Feature]:
        state = await self._pipeline_repo.get(project_id)
        if state is None:
            raise ValueError(f"No se encontro el pipeline para el proyecto {project_id}")

        new_features: list[Feature] = []
        for suggestion in selected_suggestions:
            feature = Feature(
                id=IdGenerator.generate("feature"),
                number=suggestion.number,
                title=suggestion.title,
                slug=suggestion.title.lower().replace(" ", "-"),
                description=suggestion.description,
                status=FeatureStatus.borrador,
                rationale=suggestion.rationale,
                inferred_from=suggestion.inferred_from,
            )
            new_features.append(feature)

        state.features = state.features + new_features
        from datetime import UTC, datetime

        state.updated_at = datetime.now(UTC)
        await self._pipeline_repo.save(state)
        return new_features
