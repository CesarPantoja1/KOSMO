from __future__ import annotations

from kosmo.contracts.pipeline.phase_outputs import SuggestedFeature, SuggestFeaturesOutput
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository
from kosmo.domain.pipeline.context_builder import ContextBuilder
from kosmo.domain.pipeline.kosmo_agent import KOSMOAgent
from kosmo.domain.sdd.document_converters import slugify_spanish
from kosmo.domain.sdd.id_generator import IdGenerator


class SuggestFeaturesUseCase:
    def __init__(
        self,
        agent: KOSMOAgent,
        context_builder: ContextBuilder,
        feature_repo: FeatureRepository,
    ) -> None:
        self._agent = agent
        self._context_builder = context_builder
        self._feature_repo = feature_repo

    async def execute(
        self,
        project_id: ProjectId,
    ) -> SuggestFeaturesOutput:
        context = await self._context_builder.build_suggest_features_context(project_id)
        return await self._agent.execute_suggest(context)


class SaveSelectedFeaturesUseCase:
    def __init__(self, feature_repo: FeatureRepository) -> None:
        self._feature_repo = feature_repo

    async def execute(
        self,
        project_id: ProjectId,
        selected_suggestions: list[SuggestedFeature],
    ) -> list[Feature]:
        existing = await self._feature_repo.list_by_project(project_id)
        existing_slugs = {f.slug for f in existing}

        new_features: list[Feature] = []
        for suggestion in selected_suggestions:
            base = slugify_spanish(suggestion.title)
            slug = base
            counter = 2
            while slug in existing_slugs:
                slug = f"{base}-{counter}"
                counter += 1
            existing_slugs.add(slug)
            feature = Feature(
                id=IdGenerator.generate("feature"),
                project_id=project_id,
                number=suggestion.number,
                title=suggestion.title,
                slug=slug,
                description=suggestion.description,
                rationale=suggestion.rationale,
                inferred_from=suggestion.inferred_from,
            )
            new_features.append(feature)

        await self._feature_repo.save_many(new_features)
        return new_features
