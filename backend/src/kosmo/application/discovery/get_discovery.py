from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.contracts.sdd.errors import DocumentNotFoundError
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository


@dataclass(frozen=True)
class GetDiscoveryInput:
    project_id: ProjectId


@dataclass(frozen=True)
class GetDiscoveryOutput:
    project_id: ProjectId
    document: RichTextDocument


class GetDiscoveryUseCase:
    """Caso de uso: obtiene el documento de descubrimiento almacenado de un proyecto."""

    def __init__(self, document_repo: DocumentRepository) -> None:
        self._document_repo = document_repo

    async def execute(self, input_data: GetDiscoveryInput) -> GetDiscoveryOutput:
        """Obtiene el documento de descubrimiento de un proyecto.

        Args:
            input_data: Contiene el project_id del proyecto.

        Returns:
            GetDiscoveryOutput con el documento de descubrimiento encontrado.

        Raises:
            DocumentNotFoundError: Si no existe documento de descubrimiento para el proyecto.
        """
        document = await self._document_repo.get_discovery(input_data.project_id)

        if document is None:
            raise DocumentNotFoundError(
                document_type="discovery",
                instance=f"/api/v1/projects/{input_data.project_id}/discovery",
            )

        return GetDiscoveryOutput(
            project_id=input_data.project_id,
            document=document,
        )
