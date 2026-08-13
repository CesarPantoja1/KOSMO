from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.application.knowledge import ConsolidateKnowledgePatterns
from kosmo.application.pipeline.kosmo_agent import KOSMOAgent
from kosmo.config import Settings
from kosmo.contracts.agent_memory import AgentMemoryPort, KnowledgePatternStore
from kosmo.contracts.llm.ports import Embedder, LLMClient
from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.domain.pipeline.context_builder import ContextBuilder
from kosmo.domain.pipeline.knowledge_tool_registry import KnowledgeToolRegistry
from kosmo.domain.pipeline.skill_registry import SkillRegistry
from kosmo.infrastructure.api.composition.skill_registration import build_skill_registry
from kosmo.infrastructure.llm.embedder import OpenAIEmbedder
from kosmo.infrastructure.llm.knowledge_tools import (
    build_find_similar_sessions,
    build_get_diagram_for_feature,
    build_get_downstream_artifacts,
    build_get_impact,
    build_get_phase_document,
    build_get_requirements_for_feature,
)
from kosmo.infrastructure.llm.noop_adapter import NoopLLMClient
from kosmo.infrastructure.llm.pydantic_ai_adapter import PydanticAILLMClient
from kosmo.infrastructure.persistence.memory.sqlalchemy_store import (
    SqlAlchemyAgentSessionStore,
    SqlAlchemyKnowledgePatternStore,
)
from kosmo.infrastructure.persistence.postgres.outbox import OutboxStore
from kosmo.infrastructure.persistence.postgres.registry import RepositoryRegistry


@dataclass(frozen=True, slots=True)
class PipelineComponents:
    llm_client: LLMClient
    context_builder: ContextBuilder
    agent: AgentPort
    skill_registry: SkillRegistry
    agent_memory: AgentMemoryPort
    pattern_store: KnowledgePatternStore
    validate_phase_context: Any
    process_chat_message: Any
    chat_repo: Any
    traceability_repo: Any
    outbox: Any
    consolidate_patterns: ConsolidateKnowledgePatterns


def _build_pydantic_ai_model(provider: str, model: str, api_key: str | None) -> object:
    if provider == "deepseek":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        return OpenAIChatModel(
            model,
            provider=OpenAIProvider(base_url="https://api.deepseek.com", api_key=api_key),
        )
    elif provider == "openai":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        return OpenAIChatModel(
            model,
            provider=OpenAIProvider(api_key=api_key),
        )

    return f"{provider}:{model}"


def _build_embedder(settings: Settings) -> Embedder | None:
    if settings.embedding_provider == "none":
        return None
    if settings.embedding_provider == "openai" and settings.llm_api_key:
        return OpenAIEmbedder(api_key=settings.llm_api_key.get_secret_value())
    if settings.embedding_provider == "fastembed":
        from kosmo.infrastructure.llm.local_embedder import FastembedEmbedder

        return FastembedEmbedder()
    if settings.embedding_provider == "auto":
        if settings.llm_provider.lower() == "openai" and settings.llm_api_key:
            return OpenAIEmbedder(api_key=settings.llm_api_key.get_secret_value())
        try:
            from kosmo.infrastructure.llm.local_embedder import FastembedEmbedder

            return FastembedEmbedder()
        except ImportError:
            return None
    return None


def build_pipeline_components(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    repos: RepositoryRegistry,
) -> PipelineComponents:
    if settings.llm_provider.lower() == "noop":
        llm_client: LLMClient = NoopLLMClient()
    else:
        api_key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
        model = _build_pydantic_ai_model(settings.llm_provider, settings.llm_model, api_key)
        llm_client = PydanticAILLMClient(model=model)

    context_builder = ContextBuilder(
        document_repo=repos.documents,
        project_repo=repos.projects,
        feature_repo=repos.features,
        requirement_repo=repos.requirements,
    )

    agent_memory = SqlAlchemyAgentSessionStore(session_factory)
    pattern_store = SqlAlchemyKnowledgePatternStore(session_factory)

    skill_registry = build_skill_registry()

    embedding_generator = _build_embedder(settings)

    knowledge_tools = KnowledgeToolRegistry()
    knowledge_tools.register(*build_get_phase_document(repos.documents))
    knowledge_tools.register(*build_get_downstream_artifacts(repos.features))
    knowledge_tools.register(*build_get_requirements_for_feature(repos.requirements))
    knowledge_tools.register(*build_get_diagram_for_feature(repos.diagrams))
    if embedding_generator is not None:
        knowledge_tools.register(*build_find_similar_sessions(agent_memory, embedding_generator))
    knowledge_tools.register(*build_get_impact(repos.traceability))

    outbox = OutboxStore(session_factory)

    agent = KOSMOAgent(
        llm_client=llm_client,
        skill_registry=skill_registry,
        memory=agent_memory,  # type: ignore[reportArgumentType]
        embedding_generator=embedding_generator,
        knowledge_tools=knowledge_tools,
        pattern_store=pattern_store,  # type: ignore[reportArgumentType]
        outbox=outbox,
    )

    from kosmo.application.chat.process_chat_message import ProcessChatMessageUseCase
    from kosmo.application.chat.validate_phase_context import ValidatePhaseContextUseCase

    validate_phase_context = ValidatePhaseContextUseCase()

    process_chat_message = ProcessChatMessageUseCase(
        chat_repo=repos.chat,
        agent=agent,
        skill_registry=skill_registry,
        project_repo=repos.projects,
    )

    consolidate_patterns = ConsolidateKnowledgePatterns(
        memory=agent_memory,
        pattern_store=pattern_store,
        llm_client=llm_client,
    )

    return PipelineComponents(
        llm_client=llm_client,
        context_builder=context_builder,
        agent=agent,
        skill_registry=skill_registry,
        agent_memory=agent_memory,
        pattern_store=pattern_store,
        validate_phase_context=validate_phase_context,
        process_chat_message=process_chat_message,
        chat_repo=repos.chat,
        traceability_repo=repos.traceability,
        outbox=outbox,
        consolidate_patterns=consolidate_patterns,
    )
