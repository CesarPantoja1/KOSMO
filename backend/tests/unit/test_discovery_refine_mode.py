import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.contracts.memory.user_preference import UserPreference
from kosmo.contracts.pipeline.phase_contexts import DiscoveryRefinePhaseContext
from kosmo.contracts.sdd.document import (
    DocumentNode,
    RichTextDocument,
    SectionHeading,
    SpecPhase,
)
from kosmo.domain.pipeline.phase_modes.discovery_refine_mode import DiscoveryRefineMode


def _a_discovery_document(
    content: str = "El producto ayuda a las familias a organizar gastos compartidos.",
    heading_text: str = "Vision del producto",
) -> RichTextDocument:
    return RichTextDocument(
        nodes=[
            DocumentNode(
                type="heading",
                heading=SectionHeading(text=heading_text, level=2, slug="vision"),
                content=content,
            ),
        ]
    )


@pytest.mark.unit
def test_discovery_refine_mode_phase_name_is_discovery() -> None:
    # Arrange
    mode = DiscoveryRefineMode()

    # Act
    phase = mode.phase_name

    # Assert
    assert phase == SpecPhase.DESCUBRIMIENTO


@pytest.mark.unit
def test_discovery_refine_mode_build_user_prompt_combines_document_and_instructions() -> None:
    # Arrange
    mode = DiscoveryRefineMode()
    document = _a_discovery_document()
    context = DiscoveryRefinePhaseContext(
        current_document=document,
        user_instructions="Hace la vision mas concisa.",
    )

    # Act
    prompt = mode.build_user_prompt(context)

    # Assert
    assert "Vision del producto" in prompt
    assert "El producto ayuda a las familias a organizar gastos compartidos." in prompt
    assert "Hace la vision mas concisa." in prompt


@pytest.mark.unit
def test_discovery_refine_mode_build_user_prompt_includes_preferences() -> None:
    # Arrange
    mode = DiscoveryRefineMode()
    document = _a_discovery_document()
    context = DiscoveryRefinePhaseContext(
        current_document=document,
        user_instructions="Refina el documento.",
        user_preferences=[
            UserPreference(id="pref_1", user_id="usr_1", rule_text="Usar lenguaje formal"),
        ],
    )

    # Act
    prompt = mode.build_user_prompt(context)

    # Assert
    assert "Usar lenguaje formal" in prompt


@pytest.mark.unit
def test_discovery_refine_mode_validate_output_accepts_business_level_document() -> None:
    # Arrange
    mode = DiscoveryRefineMode()
    refined = (
        "## Vision del producto\n\n"
        "El producto ayuda a las familias a organizar sus gastos compartidos."
    )

    # Act
    result = mode.validate_output(refined)

    # Assert
    assert result.is_valid is True
    assert result.errors == []


@pytest.mark.unit
def test_discovery_refine_mode_validate_output_rejects_technical_terms() -> None:
    # Arrange
    mode = DiscoveryRefineMode()
    refined = (
        "## Vision del producto\n\n"
        "El producto expone una API REST conectada a una base de datos PostgreSQL."
    )

    # Act
    result = mode.validate_output(refined)

    # Assert
    assert result.is_valid is False
    assert any("API" in e for e in result.errors)


@pytest.mark.unit
def test_discovery_refine_mode_validate_output_rejects_unrecognized_format() -> None:
    # Arrange
    mode = DiscoveryRefineMode()

    # Act
    result = mode.validate_output(123)

    # Assert
    assert result.is_valid is False
    assert result.errors == ["Formato de salida no reconocido"]


@pytest.mark.unit
def test_discovery_refine_mode_validate_output_reads_document_key() -> None:
    # Arrange
    mode = DiscoveryRefineMode()
    output: dict[str, str] = {
        "document": "## Vision del producto\n\nEl producto organiza gastos del hogar.",
    }

    # Act
    result = mode.validate_output(output)

    # Assert
    assert result.is_valid is True


@pytest.mark.unit
def test_discovery_refine_mode_build_retry_prompt_appends_errors() -> None:
    # Arrange
    mode = DiscoveryRefineMode()

    # Act
    retry = mode.build_retry_prompt(
        original_prompt="PROMPT BASE",
        errors=["Termino tecnico prohibido 'API' encontrado en seccion 'Vision del producto'"],
        retry_count=2,
    )

    # Assert
    assert "PROMPT BASE" in retry
    assert "intento 2" in retry
    assert "Termino tecnico prohibido 'API'" in retry


@pytest.mark.unit
def test_discovery_refine_mode_available_tools_declares_business_level_validator() -> None:
    # Arrange
    mode = DiscoveryRefineMode()

    # Act
    tools = mode.available_tools

    # Assert
    assert len(tools) == 1
    assert tools[0].name == "validate_business_level"
    assert "nivel de negocio" in tools[0].description


@pytest.mark.unit
def test_discovery_refine_mode_system_prompt_mentions_refinement() -> None:
    # Arrange
    mode = DiscoveryRefineMode()

    # Act
    prompt = mode.system_prompt

    # Assert
    assert "NIVEL DE NEGOCIO" in prompt
    assert "documento de descubrimiento" in prompt.lower()


@pytest.mark.unit
def test_discovery_refine_mode_validate_output_reads_raw_text_key() -> None:
    # Arrange
    mode = DiscoveryRefineMode()
    output: dict[str, str] = {
        "raw_text": "## Vision del producto\n\nEl producto organiza gastos del hogar.",
    }

    # Act
    result = mode.validate_output(output)

    # Assert
    assert result.is_valid is True
