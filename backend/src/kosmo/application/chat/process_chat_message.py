from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from kosmo.contracts.chat import (
    ChatRepository,
    ChatRole,
    MensajeChat,
    ModificacionChat,
    SugerenciaCambio,
)
from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import LLMInvocationError, ProjectNotFoundError
from kosmo.contracts.sdd.ids import ChatMessageId, ProjectId
from kosmo.contracts.sdd.repositories import (
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)
from kosmo.domain.sdd.chat_edit_applier import (
    apply_feature_attribute,
    apply_markdown_suggestion,
    check_fragment_terms,
)
from kosmo.domain.sdd.document_converters import document_to_markdown, markdown_to_document
from kosmo.domain.sdd.id_generator import IdGenerator

if TYPE_CHECKING:
    from kosmo.domain.pipeline.skill_registry import SkillRegistry

_MAX_CONTENT_LENGTH = 4000

_log = structlog.get_logger(__name__)

_FEATURE_ATTRIBUTES: dict[str, str] = {
    "titulo": "title",
    "título": "title",
    "descripcion": "description",
    "descripción": "description",
    "origen": "origin",
}


@dataclass(frozen=True)
class ProcessChatMessageInput:
    project_id: ProjectId
    phase: SpecPhase
    content: str
    context: Any
    context_id: str | None = None
    instance: str = ""


@dataclass(frozen=True)
class ProcessChatMessageOutput:
    project_id: ProjectId
    message: MensajeChat


class ProcessChatMessageUseCase:
    """Chat conversacional por fase con aplicacion instantanea de sugerencias.

    El agente responde con el nivel de abstraccion de la fase (chat mode) y
    cada sugerencia de cambio se aplica de inmediato y de forma deterministica.
    Las sugerencias se devuelven como cards de visualizacion con su resultado.
    """

    def __init__(
        self,
        chat_repo: ChatRepository,
        agent: AgentPort,
        *,
        skill_registry: SkillRegistry | None = None,
        project_repo: ProjectRepository | None = None,
        document_repo: DocumentRepository | None = None,
        feature_repo: FeatureRepository | None = None,
        requirement_repo: RequirementRepository | None = None,
    ) -> None:
        self._chat_repo = chat_repo
        self._agent = agent
        self._skill_registry = skill_registry
        self._project_repo = project_repo
        self._document_repo = document_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo

    async def execute(self, input_data: ProcessChatMessageInput) -> ProcessChatMessageOutput:
        content = input_data.content.strip()

        if not content:
            raise ValueError("El mensaje no puede estar vacío.")
        if len(content) > _MAX_CONTENT_LENGTH:
            raise ValueError(f"El mensaje no puede exceder {_MAX_CONTENT_LENGTH} caracteres.")

        if self._project_repo is not None:
            project = await self._project_repo.by_id(input_data.project_id)
            if project is None:
                raise ProjectNotFoundError(
                    project_id=str(input_data.project_id),
                    instance=input_data.instance,
                )

        skill_name = self._resolve_chat_skill(input_data.phase)

        history = await self._chat_repo.get_history(
            project_id=input_data.project_id,
            phase=input_data.phase,
            context_id=input_data.context_id,
        )
        prior_messages = list(history.messages) if history else []

        user_msg = MensajeChat(
            id=ChatMessageId(IdGenerator.generate("chat_message")),
            role=ChatRole.USER,
            content=content,
        )
        await self._chat_repo.save_message(
            project_id=input_data.project_id,
            phase=input_data.phase,
            message=user_msg,
            context_id=input_data.context_id,
        )

        messages = prior_messages + [user_msg]

        try:
            assistant_msg = await self._invoke_agent_with_retry(
                skill_name=skill_name,
                messages=messages,
                context=input_data.context,
                project_id=input_data.project_id,
            )
        except ValueError:
            raise
        except Exception as exc:
            _log.error("chat.llm_error", exc_info=True)
            error_msg = MensajeChat(
                id=ChatMessageId(IdGenerator.generate("chat_message")),
                role=ChatRole.ASSISTANT,
                content="No se pudo procesar la solicitud. Intenta nuevamente.",
            )
            await self._chat_repo.save_message(
                project_id=input_data.project_id,
                phase=input_data.phase,
                message=error_msg,
                context_id=input_data.context_id,
            )
            raise LLMInvocationError(
                detail="Error interno al procesar el mensaje. Reintenta más tarde.",
                instance=input_data.instance,
            ) from exc

        cards = await self._apply_suggestions(
            phase=input_data.phase,
            project_id=input_data.project_id,
            context=input_data.context,
            suggestions=list(assistant_msg.suggested_changes),
        )
        modification = self._build_modification(cards)

        final_msg = MensajeChat(
            id=assistant_msg.id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            suggested_changes=cards,
            modification=modification,
        )

        await self._chat_repo.save_message(
            project_id=input_data.project_id,
            phase=input_data.phase,
            message=final_msg,
            context_id=input_data.context_id,
        )

        return ProcessChatMessageOutput(
            project_id=input_data.project_id,
            message=final_msg,
        )

    async def _apply_suggestions(
        self,
        *,
        phase: SpecPhase,
        project_id: ProjectId,
        context: Any,
        suggestions: list[SugerenciaCambio],
    ) -> list[SugerenciaCambio]:
        applied: list[SugerenciaCambio] = []
        for sc in suggestions:
            reason = await self._apply_suggestion(phase, project_id, context, sc)
            applied.append(
                SugerenciaCambio(
                    id=sc.id,
                    section=sc.section,
                    description=sc.description,
                    diff=sc.diff,
                    rationale=sc.rationale,
                    applied=reason is None,
                    not_applied_reason=reason,
                )
            )
        return applied

    async def _apply_suggestion(
        self,
        phase: SpecPhase,
        project_id: ProjectId,
        context: Any,
        sc: SugerenciaCambio,
    ) -> str | None:
        if phase == SpecPhase.DESCUBRIMIENTO:
            return await self._apply_discovery_suggestion(project_id, context, sc)
        if phase == SpecPhase.CARACTERISTICAS:
            return await self._apply_feature_suggestion(context, sc)
        if phase == SpecPhase.REQUISITOS:
            return await self._apply_requirement_suggestion(context, sc)
        return f"Fase no soportada para cambios: {phase.value}"

    async def _apply_discovery_suggestion(
        self,
        project_id: ProjectId,
        context: Any,
        sc: SugerenciaCambio,
    ) -> str | None:
        if self._document_repo is None:
            return "Repositorio de documentos no configurado."

        terms = check_fragment_terms(SpecPhase.DESCUBRIMIENTO, sc.diff.after)
        if terms:
            return "El cambio contiene terminología prohibida: " + ", ".join(sorted(set(terms))[:5]) + "."

        current_md = document_to_markdown(context.current_document)
        new_md = apply_markdown_suggestion(
            current_md,
            section=sc.section or None,
            diff_before=sc.diff.before,
            diff_after=sc.diff.after,
        )
        if new_md is None or new_md == current_md:
            return "No se encontró el fragmento a reemplazar; el documento pudo haber cambiado."

        await self._document_repo.save_discovery(project_id, markdown_to_document(new_md))
        return None

    async def _apply_feature_suggestion(self, context: Any, sc: SugerenciaCambio) -> str | None:
        if self._feature_repo is None:
            return "Repositorio de características no configurado."

        attr = _FEATURE_ATTRIBUTES.get(sc.section.strip().lower())
        if attr is None:
            return f"Atributo desconocido: {sc.section}."

        terms = check_fragment_terms(SpecPhase.CARACTERISTICAS, sc.diff.after)
        if terms:
            return "El cambio contiene terminología prohibida: " + ", ".join(sorted(set(terms))[:5]) + "."

        feature = context.feature
        current = str(getattr(feature, attr))
        new_value = apply_feature_attribute(current, diff_before=sc.diff.before, diff_after=sc.diff.after)
        if new_value is None:
            return "No se encontró el fragmento a reemplazar en el atributo."

        await self._feature_repo.save(dataclasses.replace(feature, **{attr: new_value}))
        return None

    async def _apply_requirement_suggestion(self, context: Any, sc: SugerenciaCambio) -> str | None:
        if self._requirement_repo is None:
            return "Repositorio de requisitos no configurado."

        current_md = context.requirements_markdown
        if not current_md:
            return "No hay markdown de requisitos para aplicar el cambio."

        new_md = apply_markdown_suggestion(
            current_md,
            section=None,
            diff_before=sc.diff.before,
            diff_after=sc.diff.after,
        )
        if new_md is None or new_md == current_md:
            return "No se encontró el fragmento a reemplazar; el requisito pudo haber cambiado."

        await self._requirement_repo.save(context.feature.id, new_md)
        return None

    @staticmethod
    def _build_modification(cards: list[SugerenciaCambio]) -> ModificacionChat | None:
        if not cards:
            return None

        applied = [c for c in cards if c.applied]
        if not applied:
            reasons = [c.not_applied_reason for c in cards if c.not_applied_reason]
            return ModificacionChat(applied=False, clarification_message="; ".join(reasons))

        sections = ", ".join(sorted({c.section for c in applied if c.section}))
        return ModificacionChat(
            applied=True,
            modified_section=sections or None,
            change_description="Se aplicaron los cambios sugeridos.",
        )

    async def _invoke_agent_with_retry(
        self,
        skill_name: str,
        messages: list[MensajeChat],
        context: Any,
        project_id: ProjectId,
    ) -> MensajeChat:
        @retry(
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=1, min=1, max=5),
            retry=retry_if_not_exception_type(ValueError),
            reraise=True,
        )
        async def _call() -> MensajeChat:
            return await self._agent.execute_conversation(
                skill_name=skill_name,
                messages=messages,
                context=context,
                project_id=project_id,
            )

        return await _call()

    def _resolve_chat_skill(self, phase: SpecPhase) -> str:
        if self._skill_registry is not None:
            return self._skill_registry.resolve_chat_skill(phase)
        raise ValueError(f"No hay SkillRegistry configurado para resolver el skill de chat de la fase {phase.value}")
