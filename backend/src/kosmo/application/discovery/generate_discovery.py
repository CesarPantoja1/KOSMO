from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.pipeline.phase_outputs import DiscoveryPhaseOutput
from kosmo.contracts.sdd.document import RichTextDocument, SpecPhase
from kosmo.contracts.sdd.errors import LLMInvocationError
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository, ProjectRepository
from kosmo.domain.pipeline.context_builder import ContextBuilder


@dataclass(frozen=True)
class GenerateDiscoveryInput:
    project_id: ProjectId


@dataclass(frozen=True)
class GenerateDiscoveryOutput:
    project_id: ProjectId
    document: RichTextDocument
    phase_output: DiscoveryPhaseOutput


class GenerateDiscoveryUseCase:
    """Caso de uso: genera el documento de descubrimiento mediante IA.

    Orquesta la generación del documento de descubrimiento:
    1. Verifica que el proyecto existe.
    2. Construye el contexto de fase mediante el ContextBuilder.
    3. Delega al KOSMOAgent la generación del documento.
    4. Persiste el documento resultante en el DocumentRepository.
    5. Gestiona los fallos del servicio de IA mediante LLMInvocationError.
    """

    def __init__(
        self,
        project_repo: ProjectRepository,
        document_repo: DocumentRepository,
        context_builder: ContextBuilder,
        agent: AgentPort,
    ) -> None:
        self._project_repo = project_repo
        self._document_repo = document_repo
        self._context_builder = context_builder
        self._agent = agent

    async def execute(self, input_data: GenerateDiscoveryInput) -> GenerateDiscoveryOutput:
        """Ejecuta la generación del documento de descubrimiento.

        Args:
            input_data: Contiene el project_id del proyecto a procesar.

        Returns:
            GenerateDiscoveryOutput con el documento generado y los metadatos del agente.

        Raises:
            LLMInvocationError: Si el servicio de IA falla durante la generación.
        """
        from kosmo.contracts.sdd.errors import ProjectNotFoundError

        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/discovery",
            )

        context = await self._context_builder.build_context(
            project_id=input_data.project_id,
            phase=SpecPhase.DESCUBRIMIENTO,
        )

        try:
            phase_output = await self._agent.execute(
                phase=SpecPhase.DESCUBRIMIENTO,
                context=context,
            )
        except Exception as exc:
            raise LLMInvocationError(
                detail=f"Error al generar el documento de descubrimiento: {exc}",
                instance=f"/api/v1/projects/{input_data.project_id}/discovery",
            ) from exc

        if not isinstance(phase_output, DiscoveryPhaseOutput):  # type: ignore[reportUnknownMemberType]
            raise LLMInvocationError(
                detail="El agente no devolvió un DiscoveryPhaseOutput válido.",
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
