from __future__ import annotations

import pytest

from kosmo.domain.sdd.session_title import derive_session_title


@pytest.mark.unit
def test_derive_session_title_takes_first_four_words() -> None:
    # Arrange
    content = "Como administrador quiero registrar gastos del hogar compartido"

    # Act
    title = derive_session_title(content)

    # Assert
    assert title == "Como administrador quiero registrar"


@pytest.mark.unit
def test_derive_session_title_returns_empty_for_blank_content() -> None:
    # Arrange
    content = "   \n\t "

    # Act
    title = derive_session_title(content)

    # Assert
    assert title == ""


@pytest.mark.unit
def test_derive_session_title_strips_markdown_and_punctuation() -> None:
    # Arrange
    content = "**Hola**, ¿cómo están? - Quiero ajustar los requisitos."

    # Act
    title = derive_session_title(content)

    # Assert
    assert title == "Hola cómo están quiero"


@pytest.mark.unit
def test_derive_session_title_keeps_all_words_when_under_limit() -> None:
    # Arrange
    content = "Cambia el título"

    # Act
    title = derive_session_title(content)

    # Assert
    assert title == "Cambia el título"
