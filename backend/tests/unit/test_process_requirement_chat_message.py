from __future__ import annotations

import pytest

from kosmo.application.requirements import (
    ProcessRequirementChatMessageInput,
    ProcessRequirementChatMessageUseCase,
)
from kosmo.contracts import (
    ChatMessageId,
    ChatRole,
    DiffCambio,
    MensajeChat,
    SugerenciaCambio,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import FeatureNotFoundError, LLMInvocationError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, RequirementId
from kosmo.domain.pipeline.context_builder import ContextBuilder
from kosmo.domain.sdd.document_converters import markdown_to_document
from tests.unit.fakes import (
    InMemoryChatRepository,
    InMemoryDocumentRepository,
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
    InMemoryRequirementRepository,
)

_EARS_MARKDOWN = (
    "### REQ-1.1 Validacion de timeout en conexiones\n\n"
    "**Basado en eventos**\n\n"
    "CUANDO se detecte un timeout en la conexion, "
    "el sistema debe notificar al usuario con un mensaje de error.\n\n"
    "**Criterios de Aceptacion**\n\n"
    "**Escenario: Timeout detectado al enviar datos**\n\n"
    "- **Dado** que el usuario esta enviando datos al servidor\n"
    "- **Cuando** la conexion excede los 30 segundos sin respuesta\n"
    "- **Entonces** el sistema muestra un mensaje Error de conexion\n\n"
    "**Escenario: Timeout en sincronizacion**\n\n"
    "- **Dado** que el sistema esta sincronizando datos en segundo plano\n"
    "- **Cuando** la sincronizacion falla por timeout\n"
    "- **Entonces** el sistema programa un reintento automatico en 5 minutos\n\n"
    "### REQ-1.2 Registro de eventos de error\n\n"
    "**Ubicuo**\n\n"
    "El sistema debe registrar todos los eventos de error en un log estructurado.\n\n"
    "**Criterios de Aceptacion**\n\n"
    "**Escenario: Log de evento de error**\n\n"
    "- **Dado** que ocurre un error en cualquier modulo del sistema\n"
    "- **Cuando** el error es capturado por el manejador global\n"
    "- **Entonces** se almacena en el log con timestamp y stack trace\n\n"
    "**Escenario: Consulta de logs**\n\n"
    "- **Dado** que existen logs de errores almacenados\n"
    "- **Cuando** un administrador solicita los logs del ultimo dia\n"
    "- **Entonces** el sistema retorna la lista filtrada por fecha\n"
)


def _make_feature(feature_id: str = "feat_test") -> Feature:
    return Feature(
        id=FeatureId(feature_id),
        number=1,
        title="Gestion de catalogo de productos",
        slug="gestion-catalogo-productos",
        description="El usuario administra el catalogo de productos del sistema.",
        project_id=ProjectId("prj_test"),
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


def _make_use_case(feature_repo, requirement_repo, document_repo, chat_repo, agent):
    return ProcessRequirementChatMessageUseCase(
        document_repo=document_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        chat_repo=chat_repo,
        agent=agent,  # type: ignore[reportArgumentType]
        context_builder=ContextBuilder(
            document_repo,
            InMemoryProjectRepository(),
            feature_repo,
            requirement_repo,
        ),
    )


def _assistant_msg(content: str = "respuesta") -> MensajeChat:
    return MensajeChat(
        id=ChatMessageId("msg_asst"),
        role=ChatRole.ASSISTANT,
        content=content,
        suggested_change=SugerenciaCambio(
            id="chg_01",
            section="acceptance_criteria",
            description="Agregar criterio de timeout",
            diff=DiffCambio(before="Criterios existentes", after="Dado-Cuando-Entonces nuevos"),
        ),
    )


# ── Happy path ──


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_message_success() -> None:
    # Arrange
    feature = _make_feature()
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature)
    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(feature.id, _EARS_MARKDOWN)
    doc_repo = InMemoryDocumentRepository()
    doc_repo.discovery_docs[str(feature.project_id)] = markdown_to_document("## Documento")
    chat_repo = InMemoryChatRepository()
    agent = _SpyAgent(response=_assistant_msg())
    uc = _make_use_case(feature_repo, requirement_repo, doc_repo, chat_repo, agent)
    input_data = ProcessRequirementChatMessageInput(
        feature_id=feature.id,
        requirement_id=RequirementId("req_01"),
        content="Agrega un criterio de aceptacion para timeout",
    )

    # Act
    result = await uc.execute(input_data)

    # Assert
    assert result.requirement_id == RequirementId("req_01")
    assert result.message.role == ChatRole.ASSISTANT
    assert result.message.content == "respuesta"
    assert result.message.suggested_change is not None

    history = await chat_repo.get_history(feature.project_id, SpecPhase.REQUISITOS, context_id="req_01")
    assert history is not None
    assert history.message_count == 2
    msgs = list(history.messages)
    assert msgs[0].role == ChatRole.USER
    assert msgs[0].content == "Agrega un criterio de aceptacion para timeout"
    assert msgs[1].role == ChatRole.ASSISTANT

    assert agent.calls[0][0] == "requirements_chat"
    assert len(agent.calls[0][1]) == 1
    assert agent.calls[0][1][0].role == ChatRole.USER


# ── Prior history ──


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_message_includes_prior_history() -> None:
    # Arrange
    feature = _make_feature()
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature)
    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(feature.id, _EARS_MARKDOWN)
    doc_repo = InMemoryDocumentRepository()
    doc_repo.discovery_docs[str(feature.project_id)] = markdown_to_document("## Documento")
    chat_repo = InMemoryChatRepository()
    # pre-seed history — messages already in memory with random keys
    await chat_repo.save_message(
        feature.project_id,
        SpecPhase.REQUISITOS,
        MensajeChat(id=ChatMessageId("msg_old1"), role=ChatRole.USER, content="pregunta anterior"),
        context_id="req_01",
    )
    await chat_repo.save_message(
        feature.project_id,
        SpecPhase.REQUISITOS,
        MensajeChat(id=ChatMessageId("msg_old2"), role=ChatRole.ASSISTANT, content="respuesta anterior"),
        context_id="req_01",
    )
    agent = _SpyAgent(response=_assistant_msg())
    uc = _make_use_case(feature_repo, requirement_repo, doc_repo, chat_repo, agent)
    input_data = ProcessRequirementChatMessageInput(
        feature_id=feature.id,
        requirement_id=RequirementId("req_01"),
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


# ── Feature not found ──


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_message_raises_when_feature_not_found() -> None:
    # Arrange
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    doc_repo = InMemoryDocumentRepository()
    chat_repo = InMemoryChatRepository()
    agent = _SpyAgent()
    uc = _make_use_case(feature_repo, requirement_repo, doc_repo, chat_repo, agent)
    input_data = ProcessRequirementChatMessageInput(
        feature_id=FeatureId("feat_missing"),
        requirement_id=RequirementId("req_01"),
        content="Hola",
    )

    # Act & Assert
    with pytest.raises(FeatureNotFoundError):
        await uc.execute(input_data)


# ── Invalid content ──


@pytest.mark.parametrize("content", ["", "a" * 4001])
@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_message_raises_on_invalid_content(content: str) -> None:
    # Arrange
    feature = _make_feature()
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature)
    requirement_repo = InMemoryRequirementRepository()
    doc_repo = InMemoryDocumentRepository()
    chat_repo = InMemoryChatRepository()
    agent = _SpyAgent()
    uc = _make_use_case(feature_repo, requirement_repo, doc_repo, chat_repo, agent)
    input_data = ProcessRequirementChatMessageInput(
        feature_id=feature.id,
        requirement_id=RequirementId("req_01"),
        content=content,
    )

    # Act & Assert
    with pytest.raises(ValueError):
        await uc.execute(input_data)


# ── LLM invocation error ──


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_message_raises_on_llm_failure() -> None:
    # Arrange
    feature = _make_feature()
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature)
    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(feature.id, _EARS_MARKDOWN)
    doc_repo = InMemoryDocumentRepository()
    doc_repo.discovery_docs[str(feature.project_id)] = markdown_to_document("## Documento")
    chat_repo = InMemoryChatRepository()

    class _TimeoutError(Exception):
        pass

    agent = _RaisingAgent(_TimeoutError("conexion agotada"))
    uc = _make_use_case(feature_repo, requirement_repo, doc_repo, chat_repo, agent)
    input_data = ProcessRequirementChatMessageInput(
        feature_id=feature.id,
        requirement_id=RequirementId("req_01"),
        content="Hola",
    )

    # Act & Assert
    with pytest.raises(LLMInvocationError):
        await uc.execute(input_data)

    history = await chat_repo.get_history(feature.project_id, SpecPhase.REQUISITOS, context_id="req_01")
    assert history is not None
    assert history.message_count == 2
    msgs = list(history.messages)
    assert msgs[0].role == ChatRole.USER
    assert msgs[1].role == ChatRole.ASSISTANT
    assert msgs[1].error is None
    assert msgs[1].content == "No se pudo procesar la solicitud. Intenta nuevamente."


# ── Context contains parsed EARS requirement ──


@pytest.mark.asyncio
@pytest.mark.unit
async def test_context_contains_parsed_ears_requirement() -> None:
    # Arrange
    feature = _make_feature()
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature)
    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(feature.id, _EARS_MARKDOWN)
    doc_repo = InMemoryDocumentRepository()
    doc_repo.discovery_docs[str(feature.project_id)] = markdown_to_document("## Documento")
    chat_repo = InMemoryChatRepository()
    agent = _SpyAgent(response=_assistant_msg())
    uc = _make_use_case(feature_repo, requirement_repo, doc_repo, chat_repo, agent)
    input_data = ProcessRequirementChatMessageInput(
        feature_id=feature.id,
        requirement_id=RequirementId("req_01"),
        content="Hola",
    )

    # Act
    await uc.execute(input_data)

    # Assert
    _, _, context = agent.calls[0]
    req = context.requirement
    assert req.display_id == "REQ-1.1"
    assert req.title == "Validacion de timeout en conexiones"
    assert req.statement == (
        "CUANDO se detecte un timeout en la conexion, el sistema debe notificar al usuario con un mensaje de error."
    )
    assert len(req.acceptance_criteria) == 2
    assert req.acceptance_criteria[0].scenario == "Timeout detectado al enviar datos"
    assert req.acceptance_criteria[0].given == "el usuario esta enviando datos al servidor"
    assert req.acceptance_criteria[0].when == "la conexion excede los 30 segundos sin respuesta"
    assert req.acceptance_criteria[0].then == "el sistema muestra un mensaje Error de conexion"
