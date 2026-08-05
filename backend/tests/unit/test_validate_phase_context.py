import pytest

from kosmo.application.chat.validate_phase_context import (
    ValidatePhaseContextInput,
    ValidatePhaseContextUseCase,
)
from kosmo.contracts.sdd.document import SpecPhase


@pytest.mark.asyncio
@pytest.mark.unit
async def test_valid_message_belongs_to_current_phase() -> None:
    # Arrange
    uc = ValidatePhaseContextUseCase()
    input_data = ValidatePhaseContextInput(
        content="Cambia el titulo de esta caracteristica a Recepcion de inventario",
        current_phase=SpecPhase.CARACTERISTICAS,
    )

    # Act
    output = await uc.execute(input_data)

    # Assert
    assert output.is_valid is True
    assert output.redirect_message is None
    assert output.target_phase is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redirect_to_discovery_from_features() -> None:
    # Arrange
    uc = ValidatePhaseContextUseCase()
    input_data = ValidatePhaseContextInput(
        content="Quiero cambiar la visión del negocio a B2B y los objetivos generales",
        current_phase=SpecPhase.CARACTERISTICAS,
    )

    # Act
    output = await uc.execute(input_data)

    # Assert
    assert output.is_valid is False
    assert output.target_phase == "descubrimiento"
    assert "Descubrimiento" in (output.redirect_message or "")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redirect_to_requirements_from_features() -> None:
    # Arrange
    uc = ValidatePhaseContextUseCase()
    input_data = ValidatePhaseContextInput(
        content="Agrega un criterio de aceptación para timeout en Dado-Cuando-Entonces",
        current_phase=SpecPhase.CARACTERISTICAS,
    )

    # Act
    output = await uc.execute(input_data)

    # Assert
    assert output.is_valid is False
    assert output.target_phase == "requisitos"
    assert "Requisitos" in (output.redirect_message or "")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_empty_message_returns_valid() -> None:
    # Arrange
    uc = ValidatePhaseContextUseCase()
    input_data = ValidatePhaseContextInput(
        content="   ",
        current_phase=SpecPhase.CARACTERISTICAS,
    )

    # Act
    output = await uc.execute(input_data)

    # Assert
    assert output.is_valid is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_ambiguous_message_returns_valid() -> None:
    # Arrange
    uc = ValidatePhaseContextUseCase()
    input_data = ValidatePhaseContextInput(
        content="ayúdame a entender qué sigue",
        current_phase=SpecPhase.CARACTERISTICAS,
    )

    # Act
    output = await uc.execute(input_data)

    # Assert
    assert output.is_valid is True
