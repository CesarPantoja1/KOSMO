from __future__ import annotations

from dataclasses import dataclass, field

import structlog
from ulid import ULID

from kosmo.application.chat.process_chat_modification import (
    fetch_current_content,
    persist_modification,
)
from kosmo.application.consistency.evaluate_downstream import evaluate_downstream_impacts
from kosmo.contracts.chat import (
    ChatRepository,
    ChatRole,
    DiffCambio,
    MensajeChat,
    ModificacionChat,
    PlanCambio,
)
from kosmo.contracts.consistency import ConsistencyEvaluator
from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.pipeline.phase_contexts import DirectModificationContext
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import FeatureNotFoundError, ProjectNotFoundError
from kosmo.contracts.sdd.ids import ChatMessageId, FeatureId, PlanChangeId, ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)
from kosmo.domain.sdd.id_generator import IdGenerator

_log = structlog.get_logger(__name__)

_MAX_CONTENT_LENGTH = 4000

_DIRECT_MODIFICATION_SKILL = "direct_modification"


@dataclass(frozen=True)
class ProcessChatRegenerationInput:
    content: str
    document_id: str
    document_type: SpecPhase
    project_id: ProjectId | None = None
    context_id: str | None = None
    instance: str = ""


@dataclass(frozen=True)
class ProcessChatRegenerationOutput:
    project_id: ProjectId
    message: MensajeChat
    modification: ModificacionChat | None = None
    downstream_impact: list[dict[str, object]] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


class ProcessChatRegenerationUseCase:
    """Conecta el chat con la regeneracion directa de documentos.

    Aplica la modificacion sobre el documento indicado, preserva el historial
    de sesion para encadenar solicitudes consecutivas y verifica la
    consistencia unicamente hacia la derecha del flujo de trazabilidad.
    """

    def __init__(
        self,
        *,
        agent: AgentPort,
        chat_repo: ChatRepository,
        project_repo: ProjectRepository,
        document_repo: DocumentRepository,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        diagram_repo: ActivityDiagramRepository,
        evaluator: ConsistencyEvaluator,
    ) -> None:
        self._agent = agent
        self._chat_repo = chat_repo
        self._project_repo = project_repo
        self._document_repo = document_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._diagram_repo = diagram_repo
        self._evaluator = evaluator

    async def execute(self, input_data: ProcessChatRegenerationInput) -> ProcessChatRegenerationOutput:
        content = input_data.content.strip()
        if not content:
            raise ValueError("El mensaje no puede estar vacío.")
        if len(content) > _MAX_CONTENT_LENGTH:
            raise ValueError(f"El mensaje no puede exceder {_MAX_CONTENT_LENGTH} caracteres.")

        project_id = input_data.project_id
        if project_id is None:
            feature = await self._feature_repo.by_id(FeatureId(input_data.document_id))
            if feature is None:
                raise FeatureNotFoundError(feature_id=input_data.document_id)
            project_id = feature.project_id

        project = await self._project_repo.by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(project_id),
                instance=input_data.instance,
            )

        history = await self._chat_repo.get_history(
            project_id=project_id,
            phase=input_data.document_type,
            context_id=input_data.context_id,
        )
        prior_messages = list(history.messages) if history else []

        user_msg = MensajeChat(
            id=ChatMessageId(IdGenerator.generate("chat_message")),
            role=ChatRole.USER,
            content=content,
        )
        await self._chat_repo.save_message(
            project_id=project_id,
            phase=input_data.document_type,
            message=user_msg,
            context_id=input_data.context_id,
        )

        current_content = await fetch_current_content(
            document_repo=self._document_repo,
            feature_repo=self._feature_repo,
            requirement_repo=self._requirement_repo,
            document_id=input_data.document_id,
            document_type=input_data.document_type,
        )

        context = DirectModificationContext(
            current_document=current_content,
            instruction=content,
            document_type=input_data.document_type,
        )

        result = await self._agent.execute_direct_modification(
            skill_name=_DIRECT_MODIFICATION_SKILL,
            context=context,
            history=prior_messages,
            project_id=project_id,
        )

        if not result.applied:
            clarification = (
                result.clarification_message.strip()
                or "No se pudo interpretar la solicitud. Especifica la sección y el cambio deseado."
            )
            return await self._save_assistant_reply(
                input_data,
                project_id=project_id,
                content=clarification,
                modification=ModificacionChat(applied=False, clarification_message=clarification),
            )

        modified_document = result.modified_document.strip()
        await persist_modification(
            document_repo=self._document_repo,
            feature_repo=self._feature_repo,
            requirement_repo=self._requirement_repo,
            document_id=input_data.document_id,
            document_type=input_data.document_type,
            modified_content=modified_document,
        )

        change = PlanCambio(
            id=PlanChangeId(f"chg_{ULID().hex}"),
            section=result.modified_section or "",
            description=result.change_description or "",
            diff=DiffCambio(before=current_content, after=modified_document),
        )

        impacts = await evaluate_downstream_impacts(
            self._evaluator,
            source_phase=input_data.document_type,
            project_id=project_id,
            applied_changes=[change],
            feature_repo=self._feature_repo,
            requirement_repo=self._requirement_repo,
            diagram_repo=self._diagram_repo,
        )
        if impacts:
            _log.info(
                "chat.regeneration_downstream_impact",
                project_id=str(project_id),
                phase=input_data.document_type.value,
                impact_count=len(impacts),
            )

        modification = ModificacionChat(
            applied=True,
            modified_section=result.modified_section or None,
            change_description=result.change_description or None,
            modified_document=modified_document,
            before=current_content,
            after=modified_document,
        )

        reply_content = result.change_description.strip() or "Cambio aplicado al documento."

        output = await self._save_assistant_reply(
            input_data,
            project_id=project_id,
            content=reply_content,
            modification=modification,
            downstream_impact=impacts,
        )
        return output

    async def _save_assistant_reply(
        self,
        input_data: ProcessChatRegenerationInput,
        *,
        project_id: ProjectId,
        content: str,
        modification: ModificacionChat,
        downstream_impact: list[dict[str, object]] | None = None,
    ) -> ProcessChatRegenerationOutput:
        assistant_msg = MensajeChat(
            id=ChatMessageId(IdGenerator.generate("chat_message")),
            role=ChatRole.ASSISTANT,
            content=content,
            modification=modification,
        )
        await self._chat_repo.save_message(
            project_id=project_id,
            phase=input_data.document_type,
            message=assistant_msg,
            context_id=input_data.context_id,
        )
        return ProcessChatRegenerationOutput(
            project_id=project_id,
            message=assistant_msg,
            modification=modification,
            downstream_impact=downstream_impact or [],
        )
