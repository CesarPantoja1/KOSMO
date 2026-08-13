from __future__ import annotations

import json
from dataclasses import dataclass

from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    FeatureNotFoundError,
    LLMInvocationError,
)
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import (
    DocumentRepository,
    FeatureRepository,
    RequirementRepository,
)
from kosmo.domain.sdd.document_converters import document_to_markdown, markdown_to_document

_MODIFICATION_SYSTEM_PROMPT = """Eres un asistente que modifica documentos de especificacion de software.

Recibiras el contenido actual del documento y la instruccion del usuario.
Debes aplicar el cambio directamente sobre el documento y devolver el resultado en formato JSON.

Reglas:
1. Si la instruccion es clara y especifica que cambiar y en que seccion, aplica el cambio.
2. Si la instruccion es ambigua (como "cambia eso" sin especificar seccion ni contenido),
   responde con applied=false y un mensaje pidiendo clarificacion.
3. Para caracteristicas, modified_document debe contener el nuevo titulo.
4. Para requisitos y descubrimiento, modified_document debe contener el markdown completo actualizado.
5. Siempre responde en JSON con la siguiente estructura:
   - applied: bool
   - modified_document: str (documento completo modificado, o nuevo titulo para caracteristicas)
   - modified_section: str (nombre de la seccion modificada)
   - change_description: str (descripcion breve del cambio)
   - clarification_message: str (solo si applied=false, mensaje solicitando detalle)"""


@dataclass(frozen=True)
class ProcessChatModificationInput:
    text: str
    document_id: str
    document_type: SpecPhase


@dataclass(frozen=True)
class ProcessChatModificationOutput:
    success: bool
    modified_document: str | None = None
    modified_section: str | None = None
    change_description: str | None = None
    clarification_message: str | None = None


async def fetch_current_content(
    *,
    document_repo: DocumentRepository,
    feature_repo: FeatureRepository,
    requirement_repo: RequirementRepository,
    document_id: str,
    document_type: SpecPhase,
) -> str:
    if document_type == SpecPhase.DESCUBRIMIENTO:
        doc = await document_repo.get_discovery(ProjectId(document_id))
        if doc is None:
            raise DocumentNotFoundError(document_type="descubrimiento")
        return document_to_markdown(doc)

    if document_type == SpecPhase.CARACTERISTICAS:
        feature = await feature_repo.by_id(FeatureId(document_id))
        if feature is None:
            raise FeatureNotFoundError(feature_id=document_id)
        return f"Titulo: {feature.title}\nDescripcion: {feature.description}"

    if document_type == SpecPhase.REQUISITOS:
        feature = await feature_repo.by_id(FeatureId(document_id))
        if feature is None:
            raise FeatureNotFoundError(feature_id=document_id)
        markdown = await requirement_repo.by_feature_id(FeatureId(document_id))
        if not markdown:
            raise DocumentNotFoundError(document_type="requisitos")
        return markdown

    raise ValueError(f"Tipo de documento no soportado: {document_type.value}")


async def persist_modification(
    *,
    document_repo: DocumentRepository,
    feature_repo: FeatureRepository,
    requirement_repo: RequirementRepository,
    document_id: str,
    document_type: SpecPhase,
    modified_content: str,
) -> None:
    if document_type == SpecPhase.DESCUBRIMIENTO:
        doc = markdown_to_document(modified_content)
        await document_repo.save_discovery(ProjectId(document_id), doc)

    elif document_type == SpecPhase.CARACTERISTICAS:
        feature = await feature_repo.by_id(FeatureId(document_id))
        if feature is None:
            raise FeatureNotFoundError(feature_id=document_id)
        updated = Feature(
            id=feature.id,
            number=feature.number,
            title=modified_content,
            slug=feature.slug,
            description=feature.description,
            project_id=feature.project_id,
            origin=feature.origin,
        )
        await feature_repo.save(updated)

    elif document_type == SpecPhase.REQUISITOS:
        await requirement_repo.save(FeatureId(document_id), modified_content)


class ProcessChatModificationUseCase:
    def __init__(
        self,
        *,
        document_repo: DocumentRepository,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        llm_client: LLMClient,
    ) -> None:
        self._document_repo = document_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._llm_client = llm_client

    async def execute(self, input_data: ProcessChatModificationInput) -> ProcessChatModificationOutput:
        current_content = await fetch_current_content(
            document_repo=self._document_repo,
            feature_repo=self._feature_repo,
            requirement_repo=self._requirement_repo,
            document_id=input_data.document_id,
            document_type=input_data.document_type,
        )

        prompt = PromptTemplate(
            system_prompt=_MODIFICATION_SYSTEM_PROMPT,
            user_prompt=f"Documento actual:\n\n{current_content}\n\nInstruccion del usuario:\n{input_data.text}",
        )

        try:
            response = await self._llm_client.complete_json(prompt, temperature=0.1, max_tokens=4096)
        except Exception as exc:
            raise LLMInvocationError(
                detail=f"Error al procesar la modificacion: {exc}",
            ) from exc

        parsed = self._parse_response(response.text)

        if not parsed.get("applied"):
            clarification_msg = str(parsed.get("clarification_message", "No se pudo interpretar la instruccion."))
            return ProcessChatModificationOutput(
                success=False,
                clarification_message=clarification_msg,
            )

        modified_document = str(parsed.get("modified_document", ""))
        modified_section = str(parsed.get("modified_section", ""))
        change_description = str(parsed.get("change_description", ""))

        await persist_modification(
            document_repo=self._document_repo,
            feature_repo=self._feature_repo,
            requirement_repo=self._requirement_repo,
            document_id=input_data.document_id,
            document_type=input_data.document_type,
            modified_content=modified_document,
        )

        return ProcessChatModificationOutput(
            success=True,
            modified_document=modified_document,
            modified_section=modified_section,
            change_description=change_description,
        )

    @staticmethod
    def _parse_response(text: str) -> dict[str, object]:
        try:
            return json.loads(text)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            try:
                return json.loads(text.replace("'", '"'))  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                return {"applied": False}
