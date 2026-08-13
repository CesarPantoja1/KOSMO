from __future__ import annotations

import pytest

from kosmo.domain.sdd.text_normalizer import normalize_for_match


@pytest.mark.unit
def test_normalize_for_match_unifies_line_endings_and_tabs() -> None:
    # Act
    result = normalize_for_match("a\r\nb\rc\t d")

    # Assert
    assert result == "a\nb\nc d"


@pytest.mark.unit
def test_normalize_for_match_collapses_consecutive_blank_lines() -> None:
    # Act
    result = normalize_for_match("a\n\n\nb")

    # Assert
    assert result == "a\nb"


@pytest.mark.unit
def test_normalize_for_match_strips_leading_and_trailing_whitespace() -> None:
    # Act
    result = normalize_for_match("  \n texto \n  ")

    # Assert
    assert result == "texto"


@pytest.mark.unit
def test_normalize_for_match_collapses_repeated_spaces() -> None:
    # Act
    result = normalize_for_match("hola    mundo\thoy")

    # Assert
    assert result == "hola mundo hoy"
