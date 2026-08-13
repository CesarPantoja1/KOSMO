from __future__ import annotations

import pytest

from kosmo.application.chat.process_chat_regeneration import (
    ProcessChatRegenerationInput,
    ProcessChatRegenerationUseCase,
)
from kosmo.contracts.chat import ChatRole, MensajeChat
from kosmo.contracts.pipeline.phase_contexts import DirectModificationContext
from kosmo.contracts.pipeline.phase_outputs import DirectModificationResult
from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import FeatureNotFoundError, ProjectNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from kosmo.domain.sdd.document_converters import markdown_to_document
from tests.unit.fakes import (
    FakeConsistencyEvaluator,
    InMemoryActivityDiagramRepository,
    InMemoryChatRepository,
    InMemoryDocumentRepository,
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
    InMemoryRequirementRepository,
)

_DISCOVERY_MARKDOWN = (
    "## Visión del producto\n"
    "El producto ayuda a las familias a repartir gastos.\n\n"
    "## Público objetivo\n"
    "Familias numerosas con ingresos variables.\n\n"
    "## Propuesta de valor\n"
    "Transparencia total en gastos compartidos.\n"
)

_MODIFIED_DISCOVERY = (
    "## Visión del producto\n"
    "El producto ayuda a las familias a repartir gastos.\n\n"
    "## Público objetivo\n"
    "Pequeñas y medianas empresas.\n\n"
    "## Propuesta de valor\n"
    "Transparencia total en gastos compartidos.\n"
)


class _StubRegenerationAgent:
    def __init__(self, results: list[DirectModificationResult]) -> None:
        self._results = results
        self._index = 0
        self.last_history: list[MensajeChat] | None = None

    async def execute_direct_modification(
        self,
        skill_name: str,
        context: DirectModificationContext,
        *,
        history: list[MensajeChat] | None = None,
        project_id: ProjectId | None = None,
    ) -> DirectModificationResult:
        self.last_history = history
        result = self._results[self._index] if self._index < len(self._results) else self._results[-1]
        self._index += 1
        return result


def _make_project(project_id: str = "prj_01") -> Project:
    return Project(
        id=ProjectId(project_id),
        name="GastoJusto",
        slug="gastojusto",
        description="Test",
        owner_id=UserId("usr_01"),
    )


def _make_feature(project_id: ProjectId | None = None) -> Feature:
    return Feature(
        id=FeatureId("feat_01"),
        project_id=project_id or ProjectId("prj_01"),
        number=1,
        title="Registrar gastos",
        slug="registrar-gastos",
        description="Permite registrar gastos compartidos",
    )


def _applied_result() -> DirectModificationResult:
    return DirectModificationResult(
        applied=True,
        modified_document=_MODIFIED_DISCOVERY,
        modified_section="Público objetivo",
        change_description="Se cambió el público objetivo a pequeñas y medianas empresas",
    )


def _clarification_result() -> DirectModificationResult:
    return DirectModificationResult(
        applied=False,
        clarification_message="Por favor, especifica la sección y el cambio deseado",
    )


async def _make_uc(
    *,
    agent: _StubRegenerationAgent,
    project_repo: InMemoryProjectRepository,
    document_repo: InMemoryDocumentRepository,
    feature_repo: InMemoryFeatureRepository,
    requirement_repo: InMemoryRequirementRepository,
    diagram_repo: InMemoryActivityDiagramRepository,
    chat_repo: InMemoryChatRepository,
    evaluator: FakeConsistencyEvaluator | None = None,
) -> ProcessChatRegenerationUseCase:
    return ProcessChatRegenerationUseCase(
        agent=agent,  # type: ignore[reportArgumentType]
        chat_repo=chat_repo,  # type: ignore[reportArgumentType]
        project_repo=project_repo,  # type: ignore[reportArgumentType]
        document_repo=document_repo,  # type: ignore[reportArgumentType]
        feature_repo=feature_repo,  # type: ignore[reportArgumentType]
        requirement_repo=requirement_repo,  # type: ignore[reportArgumentType]
        diagram_repo=diagram_repo,  # type: ignore[reportArgumentType]
        evaluator=evaluator or FakeConsistencyEvaluator(),
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_regeneration_applies_discovery_change_and_returns_modification() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    await project_repo.save(_make_project())
    document_repo = InMemoryDocumentRepository()
    await document_repo.save_discovery(ProjectId("prj_01"), markdown_to_document(_DISCOVERY_MARKDOWN))
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(_make_feature())
    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(FeatureId("feat_01"), "## REQ-1.1\nSistema shall calcular montos.")
    diagram_repo = InMemoryActivityDiagramRepository()
    await diagram_repo.save(
        DiagramaActividad(
            id=ActivityDiagramId("diag_01"),
            feature_id=FeatureId("feat_01"),
            diagram_syntax="@startuml\n@enduml",
        )
    )
    chat_repo = InMemoryChatRepository()

    evaluator = FakeConsistencyEvaluator()
    evaluator.set_affected_ids("modelo", ["feat_01"])

    uc = await _make_uc(
        agent=_StubRegenerationAgent([_applied_result()]),
        project_repo=project_repo,
        document_repo=document_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=diagram_repo,
        chat_repo=chat_repo,
        evaluator=evaluator,
    )

    # Act
    output = await uc.execute(
        ProcessChatRegenerationInput(
            content="Cambia el público objetivo a pequeñas y medianas empresas",
            document_id="prj_01",
            document_type=SpecPhase.DESCUBRIMIENTO,
            project_id=ProjectId("prj_01"),
            context_id=None,
            instance="/api/v1/projects/prj_01/discovery/chat",
        )
    )

    # Assert
    assert output.modification is not None
    assert output.modification.applied is True
    assert "Pequeñas y medianas empresas" in (output.modification.modified_document or "")
    assert output.modification.modified_section == "Público objetivo"
    assert output.modification.before is not None
    assert output.modification.before.strip() == _DISCOVERY_MARKDOWN.strip()

    saved = await document_repo.get_discovery(ProjectId("prj_01"))
    assert saved is not None

    roles = [m.role for m in chat_repo.messages]
    assert roles == [ChatRole.USER, ChatRole.ASSISTANT]
    assert chat_repo.messages[1].modification is not None
    assert chat_repo.messages[1].modification.applied is True

    assert len(output.downstream_impact) == 1
    assert output.downstream_impact[0]["phase"] == "model"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_regeneration_ambiguous_instruction_asks_for_clarification_without_cascade() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    await project_repo.save(_make_project())
    document_repo = InMemoryDocumentRepository()
    await document_repo.save_discovery(ProjectId("prj_01"), markdown_to_document(_DISCOVERY_MARKDOWN))
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()

    uc = await _make_uc(
        agent=_StubRegenerationAgent([_clarification_result()]),
        project_repo=project_repo,
        document_repo=document_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=diagram_repo,
        chat_repo=chat_repo,
    )

    # Act
    output = await uc.execute(
        ProcessChatRegenerationInput(
            content="Cambia eso",
            document_id="prj_01",
            document_type=SpecPhase.DESCUBRIMIENTO,
            project_id=ProjectId("prj_01"),
        )
    )

    # Assert
    assert output.modification is not None
    assert output.modification.applied is False
    assert "especifica" in (output.modification.clarification_message or "")
    assert output.downstream_impact == []

    saved = await document_repo.get_discovery(ProjectId("prj_01"))
    assert saved is not None
    roles = [m.role for m in chat_repo.messages]
    assert roles == [ChatRole.USER, ChatRole.ASSISTANT]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_regeneration_passes_session_history_on_consecutive_requests() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    await project_repo.save(_make_project())
    document_repo = InMemoryDocumentRepository()
    await document_repo.save_discovery(ProjectId("prj_01"), markdown_to_document(_DISCOVERY_MARKDOWN))
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()

    agent = _StubRegenerationAgent([_applied_result(), _applied_result()])
    uc = await _make_uc(
        agent=agent,
        project_repo=project_repo,
        document_repo=document_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=diagram_repo,
        chat_repo=chat_repo,
    )

    # Act
    await uc.execute(
        ProcessChatRegenerationInput(
            content="Cambia el público objetivo",
            document_id="prj_01",
            document_type=SpecPhase.DESCUBRIMIENTO,
            project_id=ProjectId("prj_01"),
        )
    )
    await uc.execute(
        ProcessChatRegenerationInput(
            content="Ahora cambia la propuesta de valor",
            document_id="prj_01",
            document_type=SpecPhase.DESCUBRIMIENTO,
            project_id=ProjectId("prj_01"),
        )
    )

    # Assert
    assert agent.last_history is not None
    assert len(agent.last_history) == 2
    assert agent.last_history[0].content == "Cambia el público objetivo"
    assert agent.last_history[1].role == ChatRole.ASSISTANT


@pytest.mark.asyncio
@pytest.mark.unit
async def test_regeneration_updates_feature_title() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    await project_repo.save(_make_project())
    document_repo = InMemoryDocumentRepository()
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(_make_feature())
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()

    feature_result = DirectModificationResult(
        applied=True,
        modified_document="Registrar y editar gastos",
        modified_section="Título",
        change_description="Se modificó el título de la característica",
    )
    uc = await _make_uc(
        agent=_StubRegenerationAgent([feature_result]),
        project_repo=project_repo,
        document_repo=document_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=diagram_repo,
        chat_repo=chat_repo,
    )

    # Act
    output = await uc.execute(
        ProcessChatRegenerationInput(
            content="Cambia el título a 'Registrar y editar gastos'",
            document_id="feat_01",
            document_type=SpecPhase.CARACTERISTICAS,
            project_id=None,
            context_id="feat_01",
        )
    )

    # Assert
    assert output.modification is not None
    assert output.modification.applied is True
    updated = await feature_repo.by_id(FeatureId("feat_01"))
    assert updated is not None
    assert updated.title == "Registrar y editar gastos"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_regeneration_updates_requirements_markdown() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    await project_repo.save(_make_project())
    document_repo = InMemoryDocumentRepository()
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(_make_feature())
    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(FeatureId("feat_01"), "## REQ-1.1\nSistema shall calcular montos.")
    diagram_repo = InMemoryActivityDiagramRepository()
    chat_repo = InMemoryChatRepository()

    req_result = DirectModificationResult(
        applied=True,
        modified_document="## REQ-1.1\nSistema shall calcular montos con dos decimales.",
        modified_section="REQ-1.1",
        change_description="Se agregó precisión de dos decimales a REQ-1.1",
    )
    uc = await _make_uc(
        agent=_StubRegenerationAgent([req_result]),
        project_repo=project_repo,
        document_repo=document_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=diagram_repo,
        chat_repo=chat_repo,
    )

    # Act
    output = await uc.execute(
        ProcessChatRegenerationInput(
            content="Agrega dos decimales al requisito REQ-1.1",
            document_id="feat_01",
            document_type=SpecPhase.REQUISITOS,
            project_id=None,
            context_id="feat_01",
        )
    )

    # Assert
    assert output.modification is not None
    assert output.modification.applied is True
    saved = await requirement_repo.by_feature_id(FeatureId("feat_01"))
    assert saved is not None
    assert "dos decimales" in saved


@pytest.mark.asyncio
@pytest.mark.unit
async def test_regeneration_raises_when_project_not_found() -> None:
    # Arrange
    uc = await _make_uc(
        agent=_StubRegenerationAgent([_applied_result()]),
        project_repo=InMemoryProjectRepository(),
        document_repo=InMemoryDocumentRepository(),
        feature_repo=InMemoryFeatureRepository(),
        requirement_repo=InMemoryRequirementRepository(),
        diagram_repo=InMemoryActivityDiagramRepository(),
        chat_repo=InMemoryChatRepository(),
    )

    # Act & Assert
    with pytest.raises(ProjectNotFoundError):
        await uc.execute(
            ProcessChatRegenerationInput(
                content="Cambia la visión",
                document_id="prj_missing",
                document_type=SpecPhase.DESCUBRIMIENTO,
                project_id=ProjectId("prj_missing"),
            )
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_regeneration_raises_when_feature_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    await project_repo.save(_make_project())
    uc = await _make_uc(
        agent=_StubRegenerationAgent([_applied_result()]),
        project_repo=project_repo,
        document_repo=InMemoryDocumentRepository(),
        feature_repo=InMemoryFeatureRepository(),
        requirement_repo=InMemoryRequirementRepository(),
        diagram_repo=InMemoryActivityDiagramRepository(),
        chat_repo=InMemoryChatRepository(),
    )

    # Act & Assert
    with pytest.raises(FeatureNotFoundError):
        await uc.execute(
            ProcessChatRegenerationInput(
                content="Cambia el título",
                document_id="feat_missing",
                document_type=SpecPhase.CARACTERISTICAS,
                project_id=None,
            )
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_regeneration_raises_on_empty_content() -> None:
    # Arrange
    uc = await _make_uc(
        agent=_StubRegenerationAgent([_applied_result()]),
        project_repo=InMemoryProjectRepository(),
        document_repo=InMemoryDocumentRepository(),
        feature_repo=InMemoryFeatureRepository(),
        requirement_repo=InMemoryRequirementRepository(),
        diagram_repo=InMemoryActivityDiagramRepository(),
        chat_repo=InMemoryChatRepository(),
    )

    # Act & Assert
    with pytest.raises(ValueError, match="vacío"):
        await uc.execute(
            ProcessChatRegenerationInput(
                content="   ",
                document_id="prj_01",
                document_type=SpecPhase.DESCUBRIMIENTO,
                project_id=ProjectId("prj_01"),
            )
        )
