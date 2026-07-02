from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.pipeline.phase_contexts import FeaturesPhaseContext
from kosmo.contracts.pipeline.phase_outputs import (
    FeaturesPhaseOutput,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import LLMInvocationError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import (
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
)


@dataclass(frozen=True)
class GenerateFeaturesInput:
    project_id: ProjectId


@dataclass(frozen=True)
class GenerateFeaturesOutput:
    project_id: ProjectId
    features: list[Feature]
    phase_output: FeaturesPhaseOutput


class GenerateFeaturesUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        document_repo: DocumentRepository,
        feature_repo: FeatureRepository,
        agent: AgentPort,
    ) -> None:
        self._project_repo = project_repo
        self._document_repo = document_repo
        self._feature_repo = feature_repo
        self._agent = agent

    async def execute(self, input_data: GenerateFeaturesInput) -> GenerateFeaturesOutput:
        from kosmo.contracts.sdd.errors import (
            DocumentNotFoundError,
            ProjectNotFoundError,
        )

        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/features",
            )

        discovery_doc = await self._document_repo.get_discovery(input_data.project_id)
        if discovery_doc is None:
            raise DocumentNotFoundError(
                document_type="discovery",
                instance=f"/api/v1/projects/{input_data.project_id}/features",
            )

        existing_features = await self._feature_repo.list_by_project(input_data.project_id)
        existing_titles = [f.title for f in existing_features]

        context = FeaturesPhaseContext(
            discovery_document=discovery_doc,
            existing_feature_titles=existing_titles,
            project_id=input_data.project_id,
        )

        try:
            phase_output = await self._agent.execute(
                phase=SpecPhase.CARACTERISTICAS,
                context=context,
            )
        except Exception as exc:
            raise LLMInvocationError(
                detail=f"Error al generar características: {exc}",
                instance=f"/api/v1/projects/{input_data.project_id}/features",
            ) from exc

        if not isinstance(phase_output, FeaturesPhaseOutput):
            raise LLMInvocationError(
                detail="El agente no devolvió un FeaturesPhaseOutput válido.",
                instance=f"/api/v1/projects/{input_data.project_id}/features",
            )

        next_num = max((f.number for f in existing_features), default=0) + 1
        for feat in phase_output.features:
            feat.number = next_num
            feat.project_id = input_data.project_id
            next_num += 1

        saved_features = await self._feature_repo.save_many(phase_output.features)

        return GenerateFeaturesOutput(
            project_id=input_data.project_id,
            features=saved_features,
            phase_output=phase_output,
        )
