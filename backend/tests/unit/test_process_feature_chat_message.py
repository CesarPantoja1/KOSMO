import pytest

from kosmo.application.features.process_feature_chat_message import (
    ProcessFeatureChatMessageInput,
    ProcessFeatureChatMessageUseCase,
)
from kosmo.contracts import (
    ChatMessageId,
    ChatRole,
    DiffCambio,
    MensajeChat,
    SugerenciaCambio,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import (
    FeatureNotFoundError,
    LLMInvocationError,
)
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from kosmo.domain.pipeline.context_builder import ContextBuilder
from kosmo.domain.sdd.document_converters import markdown_to_document
from tests.unit.fakes import (
    InMemoryChatRepository,
    InMemoryDocumentRepository,
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
)


class _SpyAgent:
    def __init__(self, response: MensajeChat | None = None):
        self._response = response or MensajeChat(
            id=ChatMessageId("msg_assistant"),
            role=ChatRole.ASSISTANT,
            content="respuesta",
        )
        self.calls: list[tuple] = []

    async def execute_conversation(self, skill_name, messages, context):
        self.calls.append((skill_name, list(messages), context))
        return self._response

    async def execute_with_skill(self, skill_name, context, *, project_id=None, user_instructions=None):
        return None


class _RaisingAgent:
    def __init__(self, exc: Exception):
        self._exc = exc
        self.call_count = 0

    async def execute_conversation(self, skill_name, messages, context):
        self.call_count += 1
        raise self._exc

    async def execute_with_skill(self, skill_name, context, *, project_id=None, user_instructions=None):
        return None


def _make_project(project_id: str = "prj_test") -> Project:
    return Project(
        id=ProjectId(project_id),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_test"),
    )


def _make_feature(feature_id: str = "feat_test") -> Feature:
    return Feature(
        id=FeatureId(feature_id),
        number=1,
        title="Featured Feature",
        slug="featured-feature",
        description="Test feature",
        project_id=ProjectId("prj_test"),
    )


def _make_use_case(project_repo, document_repo, feature_repo, chat_repo, agent):
    return ProcessFeatureChatMessageUseCase(
        project_repo=project_repo,
        document_repo=document_repo,
        feature_repo=feature_repo,
        chat_repo=chat_repo,
        agent=agent,  # type: ignore[reportArgumentType]
        context_builder=ContextBuilder(document_repo, project_repo, feature_repo),
    )


def _assistant_msg(content: str = "respuesta") -> MensajeChat:
    return MensajeChat(
        id=ChatMessageId("msg_asst"),
        role=ChatRole.ASSISTANT,
        content=content,
        suggested_change=SugerenciaCambio(
            id="chg_01",
            section="Título",
            description="Cambiar título",
            diff=DiffCambio(before="antes", after="despues"),
        ),
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_message_success() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    feature = _make_feature()
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature)
    doc_repo = InMemoryDocumentRepository()
    doc_repo.discovery_docs[str(project.id)] = markdown_to_document("## Documento")
    chat_repo = InMemoryChatRepository()
    agent = _SpyAgent(response=_assistant_msg())
    uc = _make_use_case(project_repo, doc_repo, feature_repo, chat_repo, agent)
    input_data = ProcessFeatureChatMessageInput(
        feature_id=feature.id,
        content="Cambia el título para reflejar recepción de inventario",
    )

    # Act
    result = await uc.execute(input_data)

    # Assert
    assert result.feature_id == feature.id
    assert result.message.role == ChatRole.ASSISTANT
    assert result.message.content == "respuesta"
    assert result.message.suggested_change is not None

    history = await chat_repo.get_history(project.id, SpecPhase.CARACTERISTICAS)
    assert history is not None
    assert history.message_count == 2
    msgs = list(history.messages)
    assert msgs[0].role == ChatRole.USER
    assert msgs[0].content == "Cambia el título para reflejar recepción de inventario"
    assert msgs[1].role == ChatRole.ASSISTANT

    assert agent.calls[0][0] == "features_chat"
    assert len(agent.calls[0][1]) == 1
    assert agent.calls[0][1][0].role == ChatRole.USER


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_message_includes_prior_history() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    feature = _make_feature()
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature)
    doc_repo = InMemoryDocumentRepository()
    doc_repo.discovery_docs[str(project.id)] = markdown_to_document("## Documento")
    chat_repo = InMemoryChatRepository()
    chat_repo.messages = [
        MensajeChat(id=ChatMessageId("msg_old1"), role=ChatRole.USER, content="pregunta anterior"),
        MensajeChat(id=ChatMessageId("msg_old2"), role=ChatRole.ASSISTANT, content="respuesta anterior"),
    ]
    agent = _SpyAgent(response=_assistant_msg())
    uc = _make_use_case(project_repo, doc_repo, feature_repo, chat_repo, agent)
    input_data = ProcessFeatureChatMessageInput(
        feature_id=feature.id,
        content="ahora esto",
    )

    # Act
    await uc.execute(input_data)

    # Assert
    msgs = agent.calls[0][1]
    assert len(msgs) == 3
    assert msgs[0].content == "pregunta anterior"
    assert msgs[1].content == "respuesta anterior"
    assert msgs[2].content == "ahora esto"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_message_raises_when_feature_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    doc_repo = InMemoryDocumentRepository()
    feature_repo = InMemoryFeatureRepository()
    chat_repo = InMemoryChatRepository()
    agent = _SpyAgent()
    uc = _make_use_case(project_repo, doc_repo, feature_repo, chat_repo, agent)
    input_data = ProcessFeatureChatMessageInput(
        feature_id=FeatureId("feat_missing"),
        content="Hola",
    )

    # Act & Assert
    with pytest.raises(FeatureNotFoundError):
        await uc.execute(input_data)


@pytest.mark.parametrize("content", ["", "a" * 4001])
@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_message_raises_on_invalid_content(content: str) -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    feature = _make_feature()
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature)
    doc_repo = InMemoryDocumentRepository()
    chat_repo = InMemoryChatRepository()
    agent = _SpyAgent()
    uc = _make_use_case(project_repo, doc_repo, feature_repo, chat_repo, agent)
    input_data = ProcessFeatureChatMessageInput(
        feature_id=feature.id,
        content=content,
    )

    # Act & Assert
    with pytest.raises(ValueError):
        await uc.execute(input_data)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_message_retries_on_llm_timeout() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    feature = _make_feature()
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature)
    doc_repo = InMemoryDocumentRepository()
    doc_repo.discovery_docs[str(project.id)] = markdown_to_document("## Documento")
    chat_repo = InMemoryChatRepository()
    agent = _RaisingAgent(TimeoutError("connection timeout"))
    uc = _make_use_case(project_repo, doc_repo, feature_repo, chat_repo, agent)
    input_data = ProcessFeatureChatMessageInput(
        feature_id=feature.id,
        content="Hola",
    )

    # Act & Assert
    with pytest.raises(LLMInvocationError):
        await uc.execute(input_data)

    assert agent.call_count == 3

    history = await chat_repo.get_history(project.id, SpecPhase.CARACTERISTICAS)
    assert history is not None
    assert history.message_count == 2
    msgs = list(history.messages)
    assert msgs[0].role == ChatRole.USER
    assert msgs[1].role == ChatRole.ASSISTANT
    assert msgs[1].error is not None
    assert "connection timeout" in msgs[1].error


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_message_no_retry_on_value_error() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    feature = _make_feature()
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature)
    doc_repo = InMemoryDocumentRepository()
    doc_repo.discovery_docs[str(project.id)] = markdown_to_document("## Documento")
    chat_repo = InMemoryChatRepository()
    agent = _RaisingAgent(ValueError("Skill no encontrado"))
    uc = _make_use_case(project_repo, doc_repo, feature_repo, chat_repo, agent)
    input_data = ProcessFeatureChatMessageInput(
        feature_id=feature.id,
        content="Hola",
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Skill"):
        await uc.execute(input_data)

    assert agent.call_count == 1

    history = await chat_repo.get_history(project.id, SpecPhase.CARACTERISTICAS)
    assert history is not None
    assert history.message_count == 1
    assert history.messages[0].role == ChatRole.USER
    assert history.messages[0].error is None
