from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from kosmo.contracts.chat import ChatRepository, ChatRole, MensajeChat
from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import LLMInvocationError, ProjectNotFoundError
from kosmo.contracts.sdd.ids import ChatMessageId, ProjectId
from kosmo.contracts.sdd.repositories import ProjectRepository
from kosmo.domain.sdd.id_generator import IdGenerator

if TYPE_CHECKING:
    from kosmo.domain.pipeline.skill_registry import SkillRegistry

_MAX_CONTENT_LENGTH = 4000

_log = structlog.get_logger(__name__)


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
    def __init__(
        self,
        chat_repo: ChatRepository,
        agent: AgentPort,
        *,
        skill_registry: SkillRegistry | None = None,
        project_repo: ProjectRepository | None = None,
    ) -> None:
        self._chat_repo = chat_repo
        self._agent = agent
        self._skill_registry = skill_registry
        self._project_repo = project_repo

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

        await self._chat_repo.save_message(
            project_id=input_data.project_id,
            phase=input_data.phase,
            message=assistant_msg,
            context_id=input_data.context_id,
        )

        return ProcessChatMessageOutput(
            project_id=input_data.project_id,
            message=assistant_msg,
        )

    async def _invoke_agent_with_retry(
        self,
        skill_name: str,
        messages: list[MensajeChat],
        context: Any,
        project_id: ProjectId,
    ) -> MensajeChat:
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
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
