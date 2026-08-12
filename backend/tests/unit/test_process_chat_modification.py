import json
from unittest.mock import AsyncMock

import pytest
from ulid import ULID

from kosmo.application.chat.process_chat_modification import (
    ProcessChatModificationInput,
    ProcessChatModificationUseCase,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import DocumentNotFoundError, FeatureNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from tests.unit.fakes import (
    InMemoryDocumentRepository,
    InMemoryFeatureRepository,
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


@pytest.fixture
def document_repo() -> InMemoryDocumentRepository:
    return InMemoryDocumentRepository()


@pytest.fixture
def feature_repo() -> InMemoryFeatureRepository:
    return InMemoryFeatureRepository()


@pytest.fixture
def requirement_repo() -> InMemoryRequirementRepository:
    return InMemoryRequirementRepository()


@pytest.fixture
def llm_client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def use_case(
    document_repo: InMemoryDocumentRepository,
    feature_repo: InMemoryFeatureRepository,
    requirement_repo: InMemoryRequirementRepository,
    llm_client: AsyncMock,
) -> ProcessChatModificationUseCase:
    return ProcessChatModificationUseCase(
        document_repo=document_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        llm_client=llm_client,
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_modification_updates_discovery(
    use_case: ProcessChatModificationUseCase,
    document_repo: InMemoryDocumentRepository,
    llm_client: AsyncMock,
) -> None:
    # Arrange
    from kosmo.contracts.llm.ports import LLMResponse

    project_id = ProjectId(ULID().hex)
    from kosmo.domain.sdd.document_converters import markdown_to_document

    doc = markdown_to_document(_DISCOVERY_MARKDOWN)
    await document_repo.save_discovery(project_id, doc)

    llm_response = {
        "applied": True,
        "modified_document": _MODIFIED_DISCOVERY,
        "modified_section": "Público objetivo",
        "change_description": "Se cambió el público objetivo a pequeñas y medianas empresas",
    }
    llm_client.complete_json.return_value = LLMResponse(text=json.dumps(llm_response))

    input_data = ProcessChatModificationInput(
        text="Cambia el público objetivo a pequeñas y medianas empresas",
        document_id=str(project_id),
        document_type=SpecPhase.DESCUBRIMIENTO,
    )

    # Act
    result = await use_case.execute(input_data)

    # Assert
    assert result.success is True
    assert result.modified_document is not None
    assert "Pequeñas y medianas empresas" in result.modified_document
    assert result.modified_section == "Público objetivo"
    assert result.clarification_message is None

    saved = await document_repo.get_discovery(project_id)
    assert saved is not None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_modification_rejects_ambiguous_instruction(
    use_case: ProcessChatModificationUseCase,
    document_repo: InMemoryDocumentRepository,
    llm_client: AsyncMock,
) -> None:
    # Arrange
    from kosmo.contracts.llm.ports import LLMResponse

    project_id = ProjectId(ULID().hex)
    from kosmo.domain.sdd.document_converters import markdown_to_document

    doc = markdown_to_document(_DISCOVERY_MARKDOWN)
    await document_repo.save_discovery(project_id, doc)

    llm_response = {
        "applied": False,
        "clarification_message": "Por favor, especifica la sección y el cambio deseado",
    }
    llm_client.complete_json.return_value = LLMResponse(text=json.dumps(llm_response))

    input_data = ProcessChatModificationInput(
        text="Cambia eso",
        document_id=str(project_id),
        document_type=SpecPhase.DESCUBRIMIENTO,
    )

    # Act
    result = await use_case.execute(input_data)

    # Assert
    assert result.success is False
    assert result.clarification_message is not None
    assert "especifica" in result.clarification_message
    assert result.modified_document is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_modification_updates_feature(
    use_case: ProcessChatModificationUseCase,
    feature_repo: InMemoryFeatureRepository,
    llm_client: AsyncMock,
) -> None:
    # Arrange
    from kosmo.contracts.llm.ports import LLMResponse

    project_id = ProjectId(ULID().hex)
    feature = Feature(
        id=FeatureId(ULID().hex),
        project_id=project_id,
        number=1,
        title="Registrar gastos",
        slug="registrar-gastos",
        description="Permite registrar gastos compartidos",
    )
    await feature_repo.save(feature)

    llm_response = {
        "applied": True,
        "modified_document": "Registrar y editar gastos",
        "modified_section": "Título",
        "change_description": "Se modificó el título de la característica",
    }
    llm_client.complete_json.return_value = LLMResponse(text=json.dumps(llm_response))

    input_data = ProcessChatModificationInput(
        text="Cambia el título a 'Registrar y editar gastos'",
        document_id=str(feature.id),
        document_type=SpecPhase.CARACTERISTICAS,
    )

    # Act
    result = await use_case.execute(input_data)

    # Assert
    assert result.success is True
    assert result.modified_document is not None
    assert "Registrar y editar gastos" in result.modified_document

    updated = await feature_repo.by_id(feature.id)
    assert updated is not None
    assert updated.title == "Registrar y editar gastos"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_modification_updates_requirements(
    use_case: ProcessChatModificationUseCase,
    requirement_repo: InMemoryRequirementRepository,
    feature_repo: InMemoryFeatureRepository,
    llm_client: AsyncMock,
) -> None:
    # Arrange
    from kosmo.contracts.llm.ports import LLMResponse

    project_id = ProjectId(ULID().hex)
    feature = Feature(
        id=FeatureId(ULID().hex),
        project_id=project_id,
        number=1,
        title="Registrar gastos",
        slug="registrar-gastos",
        description="Feature de prueba",
    )
    await feature_repo.save(feature)
    req_md = "## REQ-1.1\nSistema shall calcular montos.\n\n## REQ-1.2\nSistema shall mostrar totales."
    await requirement_repo.save(feature.id, req_md)

    modified = (
        "## REQ-1.1\nSistema shall calcular montos con dos decimales.\n\n"
        "## REQ-1.2\nSistema shall mostrar totales."
    )

    llm_response = {
        "applied": True,
        "modified_document": modified,
        "modified_section": "REQ-1.1",
        "change_description": "Se agregó precisión de dos decimales al requisito REQ-1.1",
    }
    llm_client.complete_json.return_value = LLMResponse(text=json.dumps(llm_response))

    input_data = ProcessChatModificationInput(
        text="Agrega dos decimales al requisito REQ-1.1",
        document_id=str(feature.id),
        document_type=SpecPhase.REQUISITOS,
    )

    # Act
    result = await use_case.execute(input_data)

    # Assert
    assert result.success is True
    assert result.modified_document is not None
    assert "dos decimales" in result.modified_document

    saved = await requirement_repo.by_feature_id(feature.id)
    assert saved is not None
    assert "dos decimales" in saved


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_modification_raises_when_discovery_not_found(
    use_case: ProcessChatModificationUseCase,
) -> None:
    # Arrange
    project_id = ProjectId(ULID().hex)
    input_data = ProcessChatModificationInput(
        text="Cambia el título",
        document_id=str(project_id),
        document_type=SpecPhase.DESCUBRIMIENTO,
    )

    # Act & Assert
    with pytest.raises(DocumentNotFoundError) as exc_info:
        await use_case.execute(input_data)

    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_chat_modification_raises_when_feature_not_found(
    use_case: ProcessChatModificationUseCase,
) -> None:
    # Arrange
    missing_id = FeatureId(ULID().hex)
    input_data = ProcessChatModificationInput(
        text="Cambia el título",
        document_id=str(missing_id),
        document_type=SpecPhase.CARACTERISTICAS,
    )

    # Act & Assert
    with pytest.raises(FeatureNotFoundError) as exc_info:
        await use_case.execute(input_data)

    assert exc_info.value.problem.status == 404
