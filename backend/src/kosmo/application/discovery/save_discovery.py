from __future__ import annotations

from dataclasses import dataclass

from kosmo.application.consistency.trigger_downstream import trigger_downstream_evaluation
from kosmo.contracts.persistence.persistence import OutboxPort
from kosmo.contracts.sdd.document import RichTextDocument, SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository
from kosmo.domain.sdd.document_converters import document_to_markdown


@dataclass(frozen=True)
class SaveDiscoveryInput:
    project_id: ProjectId
    document: RichTextDocument


@dataclass(frozen=True)
class SaveDiscoveryOutput:
    project_id: ProjectId
    document: RichTextDocument


class SaveDiscoveryUseCase:
    """Caso de uso: persiste manualmente un documento de descubrimiento.

    Permite guardar o reemplazar el documento de descubrimiento de un proyecto
    sin invocar al agente de IA (por ejemplo, desde la edición manual en el frontend).
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        outbox: OutboxPort | None = None,
    ) -> None:
        self._document_repo = document_repo
        self._outbox = outbox

    async def execute(self, input_data: SaveDiscoveryInput) -> SaveDiscoveryOutput:
        """Persiste el documento de descubrimiento de un proyecto.

        Args:
            input_data: Contiene el project_id y el documento a guardar.

        Returns:
            SaveDiscoveryOutput con el documento persistido.
        """
        document = await self._document_repo.save_discovery(
            project_id=input_data.project_id,
            document=input_data.document,
        )

        await trigger_downstream_evaluation(
            self._outbox,
            project_id=input_data.project_id,
            source_phase=SpecPhase.DESCUBRIMIENTO,
            changes=[
                {
                    "section": "documento",
                    "description": "Edición manual del documento de Descubrimiento",
                    "before": "",
                    "after": document_to_markdown(document),
                }
            ],
        )

        return SaveDiscoveryOutput(
            project_id=input_data.project_id,
            document=document,
        )
