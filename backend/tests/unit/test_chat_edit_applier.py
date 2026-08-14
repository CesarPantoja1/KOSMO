from __future__ import annotations

import pytest

from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.sdd.chat_edit_applier import (
    apply_feature_attribute,
    apply_markdown_suggestion,
    check_fragment_terms,
)

_DISCOVERY_MD = (
    "## Visión del producto\n\n"
    "La plataforma ayuda a las familias a repartir gastos compartidos.\n\n"
    "## Alcance\n\n"
    "### Incluido\n"
    "- Registro de gastos compartidos\n\n"
    "### Excluido\n"
    "- Pagos electrónicos\n"
)


@pytest.mark.unit
def test_apply_markdown_suggestion_replaces_fragment() -> None:
    # Arrange
    # Act
    result = apply_markdown_suggestion(
        _DISCOVERY_MD,
        section="Alcance",
        diff_before="- Registro de gastos compartidos",
        diff_after="- Registro y edición de gastos compartidos",
    )

    # Assert
    assert result is not None
    assert "- Registro y edición de gastos compartidos" in result
    assert "- Registro de gastos compartidos\n" not in result


@pytest.mark.unit
def test_apply_markdown_suggestion_returns_none_when_fragment_missing() -> None:
    # Arrange
    # Act
    result = apply_markdown_suggestion(
        _DISCOVERY_MD,
        section="Alcance",
        diff_before="Texto inexistente",
        diff_after="nuevo contenido",
    )

    # Assert
    assert result is None


@pytest.mark.unit
def test_apply_markdown_suggestion_adds_content_when_diff_before_empty() -> None:
    # Arrange
    # Act
    result = apply_markdown_suggestion(
        _DISCOVERY_MD,
        section="Alcance",
        diff_before="",
        diff_after="- Sincronización con bancos",
    )

    # Assert
    assert result is not None
    assert "- Sincronización con bancos" in result


@pytest.mark.unit
def test_apply_feature_attribute_replaces_exact_fragment() -> None:
    # Arrange
    current = "El usuario ingresa un gasto para dividirlo entre los integrantes."

    # Act
    result = apply_feature_attribute(
        current,
        diff_before="ingresa un gasto",
        diff_after="registra y edita un gasto",
    )

    # Assert
    assert result == "El usuario registra y edita un gasto para dividirlo entre los integrantes."


@pytest.mark.unit
def test_apply_feature_attribute_replaces_normalized_fragment() -> None:
    # Arrange
    current = "El usuario  ingresa   un gasto para dividirlo."

    # Act
    result = apply_feature_attribute(current, diff_before="ingresa un gasto", diff_after="registra un gasto")

    # Assert
    assert result == "El usuario  registra un gasto para dividirlo."


@pytest.mark.unit
def test_apply_feature_attribute_returns_none_when_fragment_missing() -> None:
    # Arrange
    # Act
    result = apply_feature_attribute("El usuario ingresa un gasto.", diff_before="otra cosa", diff_after="x")

    # Assert
    assert result is None


@pytest.mark.unit
def test_apply_feature_attribute_replaces_whole_value_when_before_empty() -> None:
    # Arrange
    # Act
    result = apply_feature_attribute("texto viejo", diff_before="", diff_after="nuevo texto")

    # Assert
    assert result == "nuevo texto"


@pytest.mark.unit
def test_check_fragment_terms_detects_technical_terms_in_discovery() -> None:
    # Arrange
    # Act
    terms = check_fragment_terms(SpecPhase.DESCUBRIMIENTO, "Usaremos una base de datos PostgreSQL")

    # Assert
    assert "base de datos" in terms
    assert "PostgreSQL" in terms


@pytest.mark.unit
def test_check_fragment_terms_allows_technical_terms_in_requirements() -> None:
    # Arrange
    # Act
    terms = check_fragment_terms(SpecPhase.REQUISITOS, "El sistema debe usar PostgreSQL")

    # Assert
    assert terms == []


@pytest.mark.unit
def test_check_fragment_terms_clean_text_has_no_violations() -> None:
    # Arrange
    # Act
    terms = check_fragment_terms(SpecPhase.DESCUBRIMIENTO, "Las familias reparten gastos de forma equitativa.")

    # Assert
    assert terms == []
