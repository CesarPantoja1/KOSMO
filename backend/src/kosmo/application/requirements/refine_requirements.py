from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.pipeline.phase_contexts import RequirementsRefinePhaseContext
from kosmo.contracts.pipeline.phase_outputs import EARSPhaseOutput
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.errors import (
    FeatureNotFoundError,
    LLMInvocationError,
    ProjectNotFoundError,
    RequirementsNotFoundError,
)
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import (
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)


@dataclass(frozen=True)
class RefineRequirementsInput:
    project_id: ProjectId
    feature_id: FeatureId
    user_instructions: str


@dataclass(frozen=True)
class RefineRequirementsOutput:
    project_id: ProjectId
    feature_id: FeatureId
    requirements: list[EARSRequirement]
    phase_output: EARSPhaseOutput


class RefineRequirementsUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        agent: AgentPort,
    ) -> None:
        self._project_repo = project_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._agent = agent

    async def execute(self, input_data: RefineRequirementsInput) -> RefineRequirementsOutput:
        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements/refine",
            )

        feature = await self._feature_repo.by_id(input_data.feature_id)
        if feature is None or feature.project_id != input_data.project_id:
            raise FeatureNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements/refine",
            )

        current_markdown = await self._requirement_repo.by_feature_id(input_data.feature_id)
        if not current_markdown or not current_markdown.strip():
            raise RequirementsNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements/refine",
            )

        context = RequirementsRefinePhaseContext(
            feature=feature,
            feature_number=feature.number,
            current_requirements_markdown=current_markdown,
            user_instructions=input_data.user_instructions,
        )

        try:
            phase_output = await self._agent.execute(
                phase=SpecPhase.REQUISITOS,
                context=context,
            )
        except Exception as exc:
            raise LLMInvocationError(
                detail=f"Error al refinar requisitos EARS: {exc}",
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements/refine",
            ) from exc

        if not isinstance(phase_output, EARSPhaseOutput):
            raise LLMInvocationError(
                detail="El agente no devolvió un EARSPhaseOutput válido.",
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements/refine",
            )

        validation = phase_output.validation_result
        if not validation.is_valid or not phase_output.requirements:
            detail = "; ".join(validation.errors) or "No se generaron requisitos refinados."
            raise LLMInvocationError(
                detail=f"Los requisitos refinados no cumplen la estructura válida: {detail}",
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements/refine",
            )

        await self._requirement_repo.save(input_data.feature_id, phase_output.requirements_markdown)

        return RefineRequirementsOutput(
            project_id=input_data.project_id,
            feature_id=input_data.feature_id,
            requirements=phase_output.requirements,
            phase_output=phase_output,
        )
