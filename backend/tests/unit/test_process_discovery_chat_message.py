import pytest

from kosmo.application.discovery.process_discovery_chat_message import (
    ProcessDiscoveryChatMessageInput,
    ProcessDiscoveryChatMessageUseCase,
)
from kosmo.contracts import (
    ChatMessageId,
    ChatRole,
    DiffCambio,
    MensajeChat,
    SugerenciaCambio,
)
from kosmo.contracts.pipeline.phase_errors import PhaseTransitionError
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import (
    LLMInvocationError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from kosmo.domain.pipeline.context_builder import ContextBuilder
from kosmo.domain.sdd.document_converters import markdown_to_document
from tests.unit.fakes import (
    InMemoryChatRepository,
    InMemoryDocumentRepository,
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

    async def execute_conversation(self, skill_name, messages, context, **kwargs):
        self.calls.append((skill_name, list(messages), context))
        return self._response

    async def execute_with_skill(self, skill_name, context, *, project_id=None, user_instructions=None):
        return None


class _RaisingAgent:
    def __init__(self, exc: Exception):
        self._exc = exc
        self.call_count = 0

    async def execute_conversation(self, skill_name, messages, context, **kwargs):
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


def _make_use_case(project_repo, document_repo, chat_repo, agent):
    return ProcessDiscoveryChatMessageUseCase(
        project_repo=project_repo,
        document_repo=document_repo,
        chat_repo=chat_repo,
        agent=agent,  # type: ignore[reportArgumentType]
        context_builder=ContextBuilder(document_repo, project_repo),
    )


def _assistant_msg(content: str = "respuesta") -> MensajeChat:
    return MensajeChat(
        id=ChatMessageId("msg_asst"),
        role=ChatRole.ASSISTANT,
        content=content,
        suggested_change=SugerenciaCambio(
            id="chg_01",
            section="Alcance",
            description="Ampliar",
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
    doc_repo = InMemoryDocumentRepository()
    doc_repo.discovery_docs[str(project.id)] = markdown_to_document("## Documento")
    chat_repo = InMemoryChatRepository()
    agent = _SpyAgent(response=_assistant_msg())
    uc = _make_use_case(project_repo, doc_repo, chat_repo, agent)
    input_data = ProcessDiscoveryChatMessageInput(
        project_id=project.id,
        content="Amplia el alcance a LATAM",
    )

    # Act
    result = await uc.execute(input_data)

    # Assert
    assert result.project_id == project.id
    assert result.message.role == ChatRole.ASSISTANT
    assert result.message.content == "respuesta"
    assert result.message.suggested_change is not None

    history = await chat_repo.get_history(project.id, SpecPhase.DESCUBRIMIENTO)
    assert history is not None
    assert history.message_count == 2
    msgs = list(history.messages)
    assert msgs[0].role == ChatRole.USER
    assert msgs[0].content == "Amplia el alcance a LATAM"
    assert msgs[1].role == ChatRole.ASSISTANT

    assert agent.calls[0][0] == "discovery_chat"
    assert len(agent.calls[0][1]) == 1
    assert agent.calls[0][1][0].role == ChatRole.USER


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_message_includes_prior_history() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    doc_repo = InMemoryDocumentRepository()
    doc_repo.discovery_docs[str(project.id)] = markdown_to_document("## Documento")
    chat_repo = InMemoryChatRepository()
    chat_repo.messages = [
        MensajeChat(id=ChatMessageId("msg_old1"), role=ChatRole.USER, content="pregunta anterior"),
        MensajeChat(id=ChatMessageId("msg_old2"), role=ChatRole.ASSISTANT, content="respuesta anterior"),
    ]
    agent = _SpyAgent(response=_assistant_msg())
    uc = _make_use_case(project_repo, doc_repo, chat_repo, agent)
    input_data = ProcessDiscoveryChatMessageInput(
        project_id=project.id,
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
async def test_process_chat_message_raises_when_project_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    doc_repo = InMemoryDocumentRepository()
    chat_repo = InMemoryChatRepository()
    agent = _SpyAgent()
    uc = _make_use_case(project_repo, doc_repo, chat_repo, agent)
    input_data = ProcessDiscoveryChatMessageInput(
        project_id=ProjectId("prj_missing"),
        content="Hola",
    )

    # Act & Assert
    with pytest.raises(ProjectNotFoundError):
        await uc.execute(input_data)


@pytest.mark.parametrize("content", ["", "a" * 4001])
@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_message_raises_on_invalid_content(content: str) -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    doc_repo = InMemoryDocumentRepository()
    chat_repo = InMemoryChatRepository()
    agent = _SpyAgent()
    uc = _make_use_case(project_repo, doc_repo, chat_repo, agent)
    input_data = ProcessDiscoveryChatMessageInput(
        project_id=project.id,
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
    doc_repo = InMemoryDocumentRepository()
    doc_repo.discovery_docs[str(project.id)] = markdown_to_document("## Documento")
    chat_repo = InMemoryChatRepository()
    agent = _RaisingAgent(TimeoutError("connection timeout"))
    uc = _make_use_case(project_repo, doc_repo, chat_repo, agent)
    input_data = ProcessDiscoveryChatMessageInput(
        project_id=project.id,
        content="Hola",
    )

    # Act & Assert
    with pytest.raises(LLMInvocationError):
        await uc.execute(input_data)

    assert agent.call_count == 3

    history = await chat_repo.get_history(project.id, SpecPhase.DESCUBRIMIENTO)
    assert history is not None
    assert history.message_count == 2
    msgs = list(history.messages)
    assert msgs[0].role == ChatRole.USER
    assert msgs[1].role == ChatRole.ASSISTANT
    assert msgs[1].error is None
    assert msgs[1].content == "No se pudo procesar la solicitud. Intenta nuevamente."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_message_no_retry_on_value_error() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    doc_repo = InMemoryDocumentRepository()
    doc_repo.discovery_docs[str(project.id)] = markdown_to_document("## Documento")
    chat_repo = InMemoryChatRepository()
    agent = _RaisingAgent(ValueError("Skill no encontrado"))
    uc = _make_use_case(project_repo, doc_repo, chat_repo, agent)
    input_data = ProcessDiscoveryChatMessageInput(
        project_id=project.id,
        content="Hola",
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Skill"):
        await uc.execute(input_data)

    assert agent.call_count == 1

    history = await chat_repo.get_history(project.id, SpecPhase.DESCUBRIMIENTO)
    assert history is not None
    assert history.message_count == 1
    assert history.messages[0].role == ChatRole.USER
    assert history.messages[0].error is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_message_raises_when_discovery_document_missing() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    doc_repo = InMemoryDocumentRepository()
    chat_repo = InMemoryChatRepository()
    agent = _SpyAgent()
    uc = _make_use_case(project_repo, doc_repo, chat_repo, agent)
    input_data = ProcessDiscoveryChatMessageInput(
        project_id=project.id,
        content="Hola",
    )

    # Act & Assert
    with pytest.raises(PhaseTransitionError):
        await uc.execute(input_data)
