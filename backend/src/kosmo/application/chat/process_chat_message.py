from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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

_MAX_CONTENT_LENGTH = 4000

_log = structlog.get_logger(__name__)

# ponytail: mapping hardcodeado; el nombre del skill debería derivarse del PhaseMode
_SKILL_BY_PHASE: dict[SpecPhase, str] = {
    SpecPhase.DESCUBRIMIENTO: "discovery_chat",
    SpecPhase.CARACTERISTICAS: "features_chat",
    SpecPhase.REQUISITOS: "requirements_chat",
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
    def __init__(
        self,
        chat_repo: ChatRepository,
        agent: AgentPort,
        project_repo: ProjectRepository | None = None,
    ) -> None:
        self._chat_repo = chat_repo
        self._agent = agent
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

        skill_name = _SKILL_BY_PHASE[input_data.phase]

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
            )

        return await _call()
