from __future__ import annotations

from typing import Any

import pytest

from kosmo.application.chat.process_chat_message import (
    ProcessChatMessageInput,
    ProcessChatMessageUseCase,
)
from kosmo.contracts.chat import (
    ChatMessageId,
    ChatRole,
    DiffCambio,
    MensajeChat,
    SugerenciaCambio,
)
from kosmo.contracts.pipeline.orchestrator_ports import Skill
from kosmo.contracts.pipeline.phase_contexts import (
    DiscoveryChatContext,
    FeatureChatContext,
    RequirementChatContext,
)
from kosmo.contracts.sdd.document import EARSPattern, SpecPhase
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, RequirementId
from kosmo.domain.pipeline.phase_modes.discovery_chat_mode import DiscoveryChatMode
from kosmo.domain.pipeline.skill_registry import SkillRegistry
from kosmo.domain.sdd.document_converters import document_to_markdown, markdown_to_document
from tests.unit.conftest import DISCOVERY_VALID
from tests.unit.fakes import (
    InMemoryChatRepository,
    InMemoryDocumentRepository,
    InMemoryFeatureRepository,
    InMemoryRequirementRepository,
)


class _StubConversationAgent:
    def __init__(self, message: MensajeChat) -> None:
        self._message = message
        self.last_skill_name: str | None = None

    async def execute_conversation(
        self,
        skill_name: str,
        messages: list[MensajeChat],  # noqa: ARG002
        context: Any,  # noqa: ARG002
        *,
        project_id: ProjectId | None = None,  # noqa: ARG002
    ) -> MensajeChat:
        self.last_skill_name = skill_name
        return self._message


def _registry(phase: SpecPhase) -> SkillRegistry:
    name = {
        SpecPhase.DESCUBRIMIENTO: "discovery_chat",
        SpecPhase.CARACTERISTICAS: "features_chat",
        SpecPhase.REQUISITOS: "requirements_chat",
    }[phase]
    registry = SkillRegistry()
    registry.register(Skill(name=name, description="chat de fase", phase=phase, mode=DiscoveryChatMode()))
    return registry


def _assistant_message(*, suggestions: list[SugerenciaCambio] | None = None) -> MensajeChat:
    return MensajeChat(
        id=ChatMessageId("msg_assistant"),
        role=ChatRole.ASSISTANT,
        content="He aplicado el cambio.",
        suggested_changes=suggestions,
    )


def _a_discovery_suggestion(before: str, after: str, *, section: str = "Visión del producto") -> SugerenciaCambio:
    return SugerenciaCambio(
        id="chg_1",
        section=section,
        description="Ampliar la visión",
        diff=DiffCambio(before=before, after=after),
    )


# ── discovery ──


@pytest.mark.unit
@pytest.mark.asyncio
async def test_discovery_chat_applies_suggestion_and_returns_cards() -> None:
    # Arrange
    doc = markdown_to_document(DISCOVERY_VALID)
    ctx = DiscoveryChatContext(current_document=doc)
    agent = _StubConversationAgent(
        _assistant_message(
            suggestions=[
                _a_discovery_suggestion(
                    before="organizar y repartir gastos compartidos",
                    after="organizar y repartir gastos en LATAM",
                )
            ]
        )
    )
    chat_repo = InMemoryChatRepository()
    docs = InMemoryDocumentRepository()
    docs.discovery_docs["prj_01"] = doc
    uc = ProcessChatMessageUseCase(
        chat_repo=chat_repo,
        agent=agent,  # type: ignore[reportArgumentType]
        skill_registry=_registry(SpecPhase.DESCUBRIMIENTO),
        document_repo=docs,
    )

    # Act
    output = await uc.execute(
        ProcessChatMessageInput(
            project_id=ProjectId("prj_01"),
            phase=SpecPhase.DESCUBRIMIENTO,
            content="Amplía la visión a LATAM",
            context=ctx,
        )
    )

    # Assert
    card = output.message.suggested_changes[0]
    assert card.applied is True
    assert card.not_applied_reason is None
    assert output.message.modification is not None
    assert output.message.modification.applied is True
    assert "gastos en LATAM" in document_to_markdown(docs.discovery_docs["prj_01"])
    assert len(chat_repo.messages) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_suggestion_not_applied_when_fragment_missing() -> None:
    # Arrange
    doc = markdown_to_document(DISCOVERY_VALID)
    original_md = document_to_markdown(doc)
    ctx = DiscoveryChatContext(current_document=doc)
    agent = _StubConversationAgent(
        _assistant_message(suggestions=[_a_discovery_suggestion(before="fragmento que no existe", after="nuevo")])
    )
    chat_repo = InMemoryChatRepository()
    docs = InMemoryDocumentRepository()
    docs.discovery_docs["prj_01"] = doc
    uc = ProcessChatMessageUseCase(
        chat_repo=chat_repo,
        agent=agent,  # type: ignore[reportArgumentType]
        skill_registry=_registry(SpecPhase.DESCUBRIMIENTO),
        document_repo=docs,
    )

    # Act
    output = await uc.execute(
        ProcessChatMessageInput(
            project_id=ProjectId("prj_01"),
            phase=SpecPhase.DESCUBRIMIENTO,
            content="Cambia algo",
            context=ctx,
        )
    )

    # Assert
    card = output.message.suggested_changes[0]
    assert card.applied is False
    assert card.not_applied_reason is not None
    assert output.message.modification is not None
    assert output.message.modification.applied is False
    assert document_to_markdown(docs.discovery_docs["prj_01"]) == original_md


@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversational_message_without_suggestions() -> None:
    # Arrange
    ctx = DiscoveryChatContext(current_document=markdown_to_document(DISCOVERY_VALID))
    agent = _StubConversationAgent(_assistant_message(suggestions=[]))
    chat_repo = InMemoryChatRepository()
    uc = ProcessChatMessageUseCase(
        chat_repo=chat_repo,
        agent=agent,  # type: ignore[reportArgumentType]
        skill_registry=_registry(SpecPhase.DESCUBRIMIENTO),
    )

    # Act
    output = await uc.execute(
        ProcessChatMessageInput(
            project_id=ProjectId("prj_01"),
            phase=SpecPhase.DESCUBRIMIENTO,
            content="¿Qué secciones tiene el documento?",
            context=ctx,
        )
    )

    # Assert
    assert output.message.suggested_changes == []
    assert output.message.modification is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_guardrail_blocks_forbidden_terms_in_discovery() -> None:
    # Arrange
    doc = markdown_to_document(DISCOVERY_VALID)
    original_md = document_to_markdown(doc)
    ctx = DiscoveryChatContext(current_document=doc)
    agent = _StubConversationAgent(
        _assistant_message(
            suggestions=[
                _a_discovery_suggestion(
                    before="organizar y repartir gastos compartidos",
                    after="organizar gastos con una base de datos PostgreSQL",
                )
            ]
        )
    )
    docs = InMemoryDocumentRepository()
    docs.discovery_docs["prj_01"] = doc
    uc = ProcessChatMessageUseCase(
        chat_repo=InMemoryChatRepository(),
        agent=agent,  # type: ignore[reportArgumentType]
        skill_registry=_registry(SpecPhase.DESCUBRIMIENTO),
        document_repo=docs,
    )

    # Act
    output = await uc.execute(
        ProcessChatMessageInput(
            project_id=ProjectId("prj_01"),
            phase=SpecPhase.DESCUBRIMIENTO,
            content="Cambia la visión",
            context=ctx,
        )
    )

    # Assert
    card = output.message.suggested_changes[0]
    assert card.applied is False
    assert card.not_applied_reason is not None
    assert "terminología" in card.not_applied_reason
    assert document_to_markdown(docs.discovery_docs["prj_01"]) == original_md


# ── features ──


@pytest.mark.unit
@pytest.mark.asyncio
async def test_feature_chat_updates_attribute() -> None:
    # Arrange
    feature = Feature(
        id=FeatureId("feat_01"),
        number=1,
        title="Registrar gastos compartidos",
        slug="registrar-gastos-compartidos",
        description="El usuario ingresa un gasto para dividirlo.",
        project_id=ProjectId("prj_01"),
        origin="Deriva de Metas del producto.",
    )
    ctx = FeatureChatContext(feature=feature, discovery_document=markdown_to_document(DISCOVERY_VALID))
    agent = _StubConversationAgent(
        _assistant_message(
            suggestions=[
                SugerenciaCambio(
                    id="chg_2",
                    section="Descripción",
                    description="Permitir editar gastos",
                    diff=DiffCambio(before="ingresa un gasto", after="registra y edita un gasto"),
                )
            ]
        )
    )
    feature_repo = InMemoryFeatureRepository()
    feature_repo.features["feat_01"] = feature
    uc = ProcessChatMessageUseCase(
        chat_repo=InMemoryChatRepository(),
        agent=agent,  # type: ignore[reportArgumentType]
        skill_registry=_registry(SpecPhase.CARACTERISTICAS),
        feature_repo=feature_repo,
    )

    # Act
    output = await uc.execute(
        ProcessChatMessageInput(
            project_id=ProjectId("prj_01"),
            phase=SpecPhase.CARACTERISTICAS,
            content="Permite editar gastos",
            context=ctx,
        )
    )

    # Assert
    card = output.message.suggested_changes[0]
    assert card.applied is True
    assert "registra y edita un gasto" in feature_repo.features["feat_01"].description


# ── requirements ──


@pytest.mark.unit
@pytest.mark.asyncio
async def test_requirement_chat_updates_markdown() -> None:
    # Arrange
    feature = Feature(
        id=FeatureId("feat_01"),
        number=1,
        title="Gestión de gastos",
        slug="gestion-gastos",
        description="El usuario administra los gastos.",
        project_id=ProjectId("prj_01"),
    )
    requirement = EARSRequirement(
        id=RequirementId("req_01"),
        feature_id=FeatureId("feat_01"),
        feature_number=1,
        requirement_number=1,
        title="Presentación de montos",
        pattern=EARSPattern.ubiquitous,
        statement="El sistema debe presentar los montos.",
        origin="Deriva de C01.",
    )
    markdown = "### REQ-1.1 Presentación de montos\n\n**Statement:** El sistema debe presentar los montos.\n"
    ctx = RequirementChatContext(
        requirement=requirement,
        feature=feature,
        discovery_document=markdown_to_document(DISCOVERY_VALID),
        requirements_markdown=markdown,
    )
    agent = _StubConversationAgent(
        _assistant_message(
            suggestions=[
                SugerenciaCambio(
                    id="chg_3",
                    section="Enunciado EARS",
                    description="Agregar dos decimales",
                    diff=DiffCambio(
                        before="El sistema debe presentar los montos.",
                        after="El sistema debe presentar los montos con dos decimales.",
                    ),
                )
            ]
        )
    )
    requirement_repo = InMemoryRequirementRepository()
    requirement_repo._requirements["feat_01"] = markdown  # noqa: SLF001
    uc = ProcessChatMessageUseCase(
        chat_repo=InMemoryChatRepository(),
        agent=agent,  # type: ignore[reportArgumentType]
        skill_registry=_registry(SpecPhase.REQUISITOS),
        requirement_repo=requirement_repo,
    )

    # Act
    output = await uc.execute(
        ProcessChatMessageInput(
            project_id=ProjectId("prj_01"),
            phase=SpecPhase.REQUISITOS,
            content="Agrega dos decimales a los montos",
            context=ctx,
        )
    )

    # Assert
    card = output.message.suggested_changes[0]
    assert card.applied is True
    assert "con dos decimales" in (await requirement_repo.by_feature_id(FeatureId("feat_01")) or "")
