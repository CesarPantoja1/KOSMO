from __future__ import annotations

from kosmo.contracts.pipeline.phase_outputs import EARSPhaseOutput
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository, RequirementRepository
from kosmo.domain.pipeline.context_builder import ContextBuilder
from kosmo.domain.pipeline.kosmo_agent import KOSMOAgent
from kosmo.domain.pipeline.sequential_orchestrator import SequentialOrchestrator


class GenerateEARSUseCase:
    def __init__(
        self,
        agent: KOSMOAgent,
        context_builder: ContextBuilder,
        orchestrator: SequentialOrchestrator,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
    ) -> None:
        self._agent = agent
        self._context_builder = context_builder
        self._orchestrator = orchestrator
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo

    async def execute(
        self,
        project_id: ProjectId,
        feature_id: FeatureId,
    ) -> EARSPhaseOutput:
        await self._orchestrator.validate_transition(project_id, SpecPhase.REQUISITOS)

        context = await self._context_builder.build_ears_context_for_feature(
            project_id, feature_id
        )

        output = await self._agent.execute(SpecPhase.REQUISITOS, context)

        if not isinstance(output, EARSPhaseOutput):
            raise ValueError("El agente no genero requisitos")

        await self._requirement_repo.save(feature_id, output.requirements_markdown)

        return output


class GetRequirementsUseCase:
    def __init__(
        self,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
    ) -> None:
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo

    async def execute(
        self,
        project_id: ProjectId,
        id_or_slug: str,
    ) -> str | None:
        feature_id = FeatureId(id_or_slug)

        if not id_or_slug.startswith("feat_"):
            features = await self._feature_repo.list_by_project(project_id)
            match = next((f for f in features if f.slug == id_or_slug), None)
            if match is not None:
                feature_id = match.id

        return await self._requirement_repo.by_feature_id(feature_id)
