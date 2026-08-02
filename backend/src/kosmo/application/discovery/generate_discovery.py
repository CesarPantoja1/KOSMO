from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.pipeline.phase_contexts import DiscoveryPhaseContext
from kosmo.contracts.pipeline.phase_outputs import DiscoveryPhaseOutput
from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.contracts.sdd.errors import LLMInvocationError
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository, ProjectRepository


@dataclass(frozen=True)
class GenerateDiscoveryInput:
    project_id: ProjectId


@dataclass(frozen=True)
class GenerateDiscoveryOutput:
    project_id: ProjectId
    document: RichTextDocument
    phase_output: DiscoveryPhaseOutput


class GenerateDiscoveryUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        document_repo: DocumentRepository,
        agent: AgentPort,
    ) -> None:
        self._project_repo = project_repo
        self._document_repo = document_repo
        self._agent = agent

    async def execute(self, input_data: GenerateDiscoveryInput) -> GenerateDiscoveryOutput:
        from kosmo.contracts.sdd.errors import ProjectNotFoundError

        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/discovery",
            )

        context = DiscoveryPhaseContext(
            project_name=project.name,
            project_description=project.description,
        )

        try:
            phase_output = await self._agent.execute_with_skill(
                skill_name="discovery_generate",
                context=context,
                project_id=input_data.project_id,
            )
        except Exception as exc:
            import structlog

            structlog.get_logger(__name__).error("discovery.generate_failed", exc_info=True)
            raise LLMInvocationError(
                detail=f"Error al generar el documento de descubrimiento: {exc}",
                instance=f"/api/v1/projects/{input_data.project_id}/discovery",
            ) from exc

        if not isinstance(phase_output, DiscoveryPhaseOutput):  # type: ignore[reportUnknownMemberType]
            raise LLMInvocationError(
                detail="El agente no devolvió un DiscoveryPhaseOutput válido.",
                instance=f"/api/v1/projects/{input_data.project_id}/discovery",
            )

        if phase_output.discovery_document.section_count == 0:
            raise LLMInvocationError(
                detail="El documento de descubrimiento generado está vacío.",
                instance=f"/api/v1/projects/{input_data.project_id}/discovery",
            )

        document = await self._document_repo.save_discovery(
            project_id=input_data.project_id,
            document=phase_output.discovery_document,
        )

        return GenerateDiscoveryOutput(
            project_id=input_data.project_id,
            document=document,
            phase_output=phase_output,
        )
