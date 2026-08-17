import pytest

from kosmo.contracts.pipeline.phase_contexts import DirectModificationContext
from kosmo.contracts.pipeline.phase_outputs import DirectModificationResult
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.pipeline.phase_modes.direct_modification_mode import DirectModificationMode

_DISCOVERY_MARKDOWN = (
    "## Visión del producto\n"
    "El producto ayuda a las familias a repartir gastos.\n\n"
    "## Público objetivo\n"
    "Familias numerosas.\n"
)


@pytest.fixture
def mode() -> DirectModificationMode:
    return DirectModificationMode()


@pytest.mark.unit
def test_direct_modification_mode_build_user_prompt_includes_document_and_instruction(
    mode: DirectModificationMode,
) -> None:
    # Arrange
    context = DirectModificationContext(
        current_document=_DISCOVERY_MARKDOWN,
        instruction="Cambia el público objetivo a pequeñas y medianas empresas",
        document_type=SpecPhase.DESCUBRIMIENTO,
    )

    # Act
    prompt = mode.build_user_prompt(context)

    # Assert
    assert "Público objetivo" in prompt
    assert "Cambia el público objetivo" in prompt
    assert SpecPhase.DESCUBRIMIENTO.value in prompt


@pytest.mark.unit
def test_direct_modification_mode_rejects_applied_without_document(
    mode: DirectModificationMode,
) -> None:
    # Arrange
    output = DirectModificationResult(applied=True, modified_document="")

    # Act
    result = mode.validate_output(output)

    # Assert
    assert result.is_valid is False
    assert any("modified_document" in e for e in result.errors)


@pytest.mark.unit
def test_direct_modification_mode_rejects_not_applied_without_clarification(
    mode: DirectModificationMode,
) -> None:
    # Arrange
    output = DirectModificationResult(applied=False, clarification_message="")

    # Act
    result = mode.validate_output(output)

    # Assert
    assert result.is_valid is False
    assert any("clarification_message" in e for e in result.errors)


@pytest.mark.unit
def test_direct_modification_mode_accepts_valid_applied(
    mode: DirectModificationMode,
) -> None:
    # Arrange
    output = DirectModificationResult(
        applied=True,
        modified_document="## Público objetivo\nPequeñas y medianas empresas.\n",
        modified_section="Público objetivo",
    )

    # Act
    result = mode.validate_output(output)

    # Assert
    assert result.is_valid is True
    assert result.errors == []
