from __future__ import annotations

from dataclasses import dataclass

from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from kosmo.contracts.chat import ChatRepository, ChatRole, MensajeChat
from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.pipeline.phase_contexts import FeatureChatContext
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import FeatureNotFoundError, LLMInvocationError
from kosmo.contracts.sdd.ids import ChatMessageId, FeatureId
from kosmo.contracts.sdd.repositories import DocumentRepository, FeatureRepository, ProjectRepository
from kosmo.domain.pipeline.context_builder import ContextBuilder
from kosmo.domain.sdd.id_generator import IdGenerator

_MAX_CONTENT_LENGTH = 4000


@dataclass(frozen=True)
class ProcessFeatureChatMessageInput:
    feature_id: FeatureId
    content: str


@dataclass(frozen=True)
class ProcessFeatureChatMessageOutput:
    feature_id: FeatureId
    message: MensajeChat


class ProcessFeatureChatMessageUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        document_repo: DocumentRepository,
        feature_repo: FeatureRepository,
        chat_repo: ChatRepository,
        agent: AgentPort,
        context_builder: ContextBuilder,
    ) -> None:
        self._project_repo = project_repo
        self._document_repo = document_repo
        self._feature_repo = feature_repo
        self._chat_repo = chat_repo
        self._agent = agent
        self._context_builder = context_builder

    async def execute(self, input_data: ProcessFeatureChatMessageInput) -> ProcessFeatureChatMessageOutput:
        content = input_data.content.strip()

        if not content:
            raise ValueError("El mensaje no puede estar vacío.")
        if len(content) > _MAX_CONTENT_LENGTH:
            raise ValueError(f"El mensaje no puede exceder {_MAX_CONTENT_LENGTH} caracteres.")

        feature = await self._feature_repo.by_id(input_data.feature_id)
        if feature is None:
            raise FeatureNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=f"/api/v1/features/{input_data.feature_id}/chat",
            )

        context = await self._context_builder.build_feature_chat_context(input_data.feature_id)

        history = await self._chat_repo.get_history(
            project_id=feature.project_id,
            phase=SpecPhase.CARACTERISTICAS,
            context_id=str(feature.id),
        )
        prior_messages = list(history.messages) if history else []

        user_msg = MensajeChat(
            id=ChatMessageId(IdGenerator.generate("chat_message")),
            role=ChatRole.USER,
            content=content,
        )
        await self._chat_repo.save_message(
            project_id=feature.project_id,
            phase=SpecPhase.CARACTERISTICAS,
            message=user_msg,
            context_id=str(feature.id),
        )

        messages = prior_messages + [user_msg]

        try:
            assistant_msg = await self._invoke_agent_with_retry(messages, context)
        except ValueError:
            raise
        except Exception as exc:
            error_text = str(exc)
            error_msg = MensajeChat(
                id=ChatMessageId(IdGenerator.generate("chat_message")),
                role=ChatRole.ASSISTANT,
                content="No se pudo procesar la solicitud. Intenta nuevamente.",
                error=error_text,
            )
            await self._chat_repo.save_message(
                project_id=feature.project_id,
                phase=SpecPhase.CARACTERISTICAS,
                message=error_msg,
                context_id=str(feature.id),
            )
            raise LLMInvocationError(
                detail=f"Error al procesar el mensaje del chat: {error_text}",
                instance=f"/api/v1/features/{input_data.feature_id}/chat",
            ) from exc

        await self._chat_repo.save_message(
            project_id=feature.project_id,
            phase=SpecPhase.CARACTERISTICAS,
            message=assistant_msg,
            context_id=str(feature.id),
        )

        return ProcessFeatureChatMessageOutput(
            feature_id=input_data.feature_id,
            message=assistant_msg,
        )

    async def _invoke_agent_with_retry(
        self,
        messages: list[MensajeChat],
        context: FeatureChatContext,
    ) -> MensajeChat:
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_not_exception_type(ValueError),
            reraise=True,
        )
        async def _call() -> MensajeChat:
            return await self._agent.execute_conversation(
                skill_name="features_chat",
                messages=messages,
                context=context,
            )

        return await _call()
