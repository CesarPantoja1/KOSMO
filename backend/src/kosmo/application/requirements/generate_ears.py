from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.pipeline.phase_contexts import EARSPhaseContext
from kosmo.contracts.pipeline.phase_outputs import (
    EARSPhaseOutput,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.errors import LLMInvocationError
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import (
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)


@dataclass(frozen=True)
class GenerateEARSInput:
    project_id: ProjectId
    feature_id: FeatureId


@dataclass(frozen=True)
class GenerateEARSOutput:
    project_id: ProjectId
    feature_id: FeatureId
    requirements: list[EARSRequirement]
    phase_output: EARSPhaseOutput


class GenerateEARSUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        document_repo: DocumentRepository,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        agent: AgentPort,
    ) -> None:
        self._project_repo = project_repo
        self._document_repo = document_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._agent = agent

    async def execute(self, input_data: GenerateEARSInput) -> GenerateEARSOutput:
        from kosmo.contracts.sdd.errors import (
            DocumentNotFoundError,
            FeatureNotFoundError,
            ProjectNotFoundError,
        )

        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements",
            )

        feature = await self._feature_repo.by_id(input_data.feature_id)
        if feature is None or feature.project_id != input_data.project_id:
            raise FeatureNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements",
            )

        discovery_doc = await self._document_repo.get_discovery(input_data.project_id)
        if discovery_doc is None:
            raise DocumentNotFoundError(
                document_type="discovery",
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements",
            )

        context = EARSPhaseContext(
            discovery_document=discovery_doc,
            feature=feature,
            feature_number=feature.number,
        )

        try:
            phase_output = await self._agent.execute(
                phase=SpecPhase.REQUISITOS,
                context=context,
            )
        except Exception as exc:
            raise LLMInvocationError(
                detail=f"Error al generar requisitos EARS: {exc}",
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements",
            ) from exc

        if not isinstance(phase_output, EARSPhaseOutput):
            raise LLMInvocationError(
                detail="El agente no devolvió un EARSPhaseOutput válido.",
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements",
            )

        await self._requirement_repo.save(
            input_data.feature_id, phase_output.requirements_markdown
        )

        return GenerateEARSOutput(
            project_id=input_data.project_id,
            feature_id=input_data.feature_id,
            requirements=phase_output.requirements,
            phase_output=phase_output,
        )


class GetRequirementsUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
    ) -> None:
        self._project_repo = project_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo

    async def execute(self, project_id: ProjectId, feature_id: FeatureId) -> str | None:
        from kosmo.contracts.sdd.errors import FeatureNotFoundError, ProjectNotFoundError

        project = await self._project_repo.by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(project_id),
                instance=f"/api/v1/projects/{project_id}/features/{feature_id}/requirements",
            )

        feature = await self._feature_repo.by_id(feature_id)
        if feature is None or feature.project_id != project_id:
            raise FeatureNotFoundError(
                feature_id=str(feature_id),
                instance=f"/api/v1/projects/{project_id}/features/{feature_id}/requirements",
            )

        return await self._requirement_repo.by_feature_id(feature_id)
