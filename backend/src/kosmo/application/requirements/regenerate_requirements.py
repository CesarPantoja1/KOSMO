from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.pipeline.phase_contexts import RequirementsRefinePhaseContext
from kosmo.contracts.pipeline.phase_outputs import EARSPhaseOutput
from kosmo.contracts.sdd.errors import (
    FeatureNotFoundError,
    LLMInvocationError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import (
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)


@dataclass(frozen=True)
class RegenerateRequirementsInput:
    project_id: ProjectId
    feature_id: FeatureId


@dataclass(frozen=True)
class RegenerateRequirementsOutput:
    artifact_id: str
    content: str
    phase: str


class RegenerateRequirementsUseCase:
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

    async def execute(self, input_data: RegenerateRequirementsInput) -> RegenerateRequirementsOutput:
        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/features/{input_data.feature_id}/requirements/regenerate",
            )

        feature = await self._feature_repo.by_id(input_data.feature_id)
        if feature is None or feature.project_id != input_data.project_id:
            raise FeatureNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=f"/api/v1/features/{input_data.feature_id}/requirements/regenerate",
            )

        current_markdown = await self._requirement_repo.by_feature_id(input_data.feature_id)
        if not current_markdown or not current_markdown.strip():
            raise LLMInvocationError(
                detail="No existen requisitos previos para regenerar.",
                instance=f"/api/v1/features/{input_data.feature_id}/requirements/regenerate",
            )

        user_instructions = (
            "Regenera completamente los requisitos EARS de la característica "
            f"'{feature.title}' manteniendo la estructura y los criterios de "
            "aceptación en formato Dado-Cuando-Entonces.\n\n"
            "El documento actual de requisitos es el siguiente (úsalo como base "
            "estructural):\n\n"
            f"{current_markdown}"
        )

        context = RequirementsRefinePhaseContext(
            feature=feature,
            feature_number=feature.number,
            current_requirements_markdown=current_markdown,
            user_instructions=user_instructions,
        )

        try:
            phase_output = await self._agent.execute_with_skill(
                skill_name="requirements_refine",
                context=context,
                project_id=input_data.project_id,
                user_instructions=user_instructions,
            )
        except Exception as exc:
            raise LLMInvocationError(
                detail=f"Error al regenerar requisitos EARS: {exc}",
                instance=f"/api/v1/features/{input_data.feature_id}/requirements/regenerate",
            ) from exc

        if not isinstance(phase_output, EARSPhaseOutput):
            raise LLMInvocationError(
                detail="El agente no devolvió un EARSPhaseOutput válido.",
                instance=f"/api/v1/features/{input_data.feature_id}/requirements/regenerate",
            )

        validation = phase_output.validation_result
        if not validation.is_valid or not phase_output.requirements_markdown.strip():
            detail = "; ".join(validation.errors) or "No se generaron requisitos."
            raise LLMInvocationError(
                detail=f"La regeneración de requisitos falló: {detail}",
                instance=f"/api/v1/features/{input_data.feature_id}/requirements/regenerate",
            )

        await self._requirement_repo.save(input_data.feature_id, phase_output.requirements_markdown)

        return RegenerateRequirementsOutput(
            artifact_id=str(input_data.feature_id),
            content=phase_output.requirements_markdown,
            phase="requirements",
        )
