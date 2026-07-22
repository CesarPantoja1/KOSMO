from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.pipeline.phase_contexts import ModeloPhaseContext
from kosmo.contracts.pipeline.phase_outputs import ModeloPhaseOutput
from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import (
    FeatureNotFoundError,
    LLMInvocationError,
    RequirementsNotFoundError,
)
from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    FeatureRepository,
    RequirementRepository,
)
from kosmo.domain.sdd.id_generator import IdGenerator


@dataclass(frozen=True)
class GenerateDiagramInput:
    project_id: ProjectId
    feature_id: FeatureId


@dataclass(frozen=True)
class GenerateDiagramOutput:
    diagram: DiagramaActividad
    phase_output: ModeloPhaseOutput


class GenerateActivityDiagramUseCase:
    def __init__(
        self,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        diagram_repo: ActivityDiagramRepository,
        agent: AgentPort,
    ) -> None:
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._diagram_repo = diagram_repo
        self._agent = agent

    async def execute(self, input_data: GenerateDiagramInput) -> GenerateDiagramOutput:
        feature = await self._feature_repo.by_id(input_data.feature_id)
        if feature is None or feature.project_id != input_data.project_id:
            raise FeatureNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/diagram",
            )

        ears_markdown = await self._requirement_repo.by_feature_id(input_data.feature_id)
        if not ears_markdown or not ears_markdown.strip():
            raise RequirementsNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/diagram",
            )

        context = ModeloPhaseContext(
            feature_id=input_data.feature_id,
            ears_requirements=ears_markdown,
        )

        try:
            phase_output = await self._agent.execute(
                phase=SpecPhase.MODELO,
                context=context,
            )
        except Exception as exc:
            raise LLMInvocationError(
                detail=f"Error al generar diagrama de actividad: {exc}",
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/diagram",
            ) from exc

        if not isinstance(phase_output, ModeloPhaseOutput):
            raise LLMInvocationError(
                detail="El agente no devolvió un ModeloPhaseOutput válido.",
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/diagram",
            )

        validation = phase_output.validation_result
        if not validation.is_valid or not phase_output.diagram_syntax.strip():
            detail = "; ".join(validation.errors) or "El diagrama generado está vacío."
            raise LLMInvocationError(
                detail=f"El diagrama de actividad generado no cumple la estructura válida: {detail}",
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/diagram",
            )

        diagram_id = ActivityDiagramId(IdGenerator.generate("activity_diagram"))
        diagram = DiagramaActividad(
            id=diagram_id,
            feature_id=input_data.feature_id,
            diagram_syntax=phase_output.diagram_syntax,
        )

        await self._diagram_repo.save(diagram)

        return GenerateDiagramOutput(
            diagram=diagram,
            phase_output=phase_output,
        )
