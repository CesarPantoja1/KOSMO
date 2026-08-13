from __future__ import annotations

import pytest

from kosmo.domain.sdd.section_parser import section_heading_preserved, section_spans

_MARKDOWN = "## Visión\n\nContenido de visión.\n\n## Alcance\n\nContenido de alcance."


@pytest.mark.unit
def test_section_spans_returns_heading_names_and_bounds() -> None:
    # Act
    spans = section_spans(_MARKDOWN)

    # Assert
    assert [name for name, _start, _end in spans] == ["Visión", "Alcance"]
    assert spans[0][1] == 0
    assert spans[0][2] <= spans[1][1]
    assert spans[1][2] == len(_MARKDOWN)


@pytest.mark.unit
def test_section_spans_returns_empty_for_markdown_without_headings() -> None:
    # Act
    spans = section_spans("texto plano sin headings")

    # Assert
    assert spans == []


@pytest.mark.unit
def test_section_spans_detects_any_heading_level() -> None:
    # Act
    spans = section_spans("# H1\n\ntexto\n\n### H3\n\ntexto")

    # Assert
    assert [name for name, _start, _end in spans] == ["H1", "H3"]


@pytest.mark.unit
def test_section_heading_preserved_accepts_same_heading_ignoring_spacing() -> None:
    # Act
    result = section_heading_preserved("## Alcance\n\noriginal", "##   Alcance  \n\nreescrito")

    # Assert
    assert result is True


@pytest.mark.unit
def test_section_heading_preserved_rejects_changed_heading() -> None:
    # Act
    result = section_heading_preserved("## Alcance\n\noriginal", "## Presupuesto\n\notro")

    # Assert
    assert result is False


@pytest.mark.unit
def test_section_heading_preserved_accepts_original_without_heading() -> None:
    # Act
    result = section_heading_preserved("texto sin heading", "cualquier reescritura")

    # Assert
    assert result is True
