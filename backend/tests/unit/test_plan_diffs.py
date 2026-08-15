import pytest

from kosmo.domain.sdd.discovery_diff import ChangeClass, ChangeType, SectionChange
from kosmo.domain.sdd.plan_diffs import apply_change_diff, merge_changes_with_diffs


@pytest.mark.unit
def test_replace_when_before_found() -> None:
    result = apply_change_diff("Hola mundo", before="Hola", after="Adiós")

    assert result == "Adiós mundo"


@pytest.mark.unit
def test_replace_first_occurrence_only() -> None:
    result = apply_change_diff("Hola Hola mundo", before="Hola", after="X")

    assert result == "X Hola mundo"


@pytest.mark.unit
def test_append_when_before_empty() -> None:
    result = apply_change_diff("Línea 1", before="", after="Línea 2")

    assert result == "Línea 1\n\nLínea 2"


@pytest.mark.unit
def test_append_when_before_whitespace_only() -> None:
    result = apply_change_diff("Línea 1", before="   ", after="Línea 2")

    assert result == "Línea 1\n\nLínea 2"


@pytest.mark.unit
def test_unchanged_when_after_also_empty() -> None:
    result = apply_change_diff("Línea 1", before="", after="")

    assert result == "Línea 1"


@pytest.mark.unit
def test_none_when_before_not_found() -> None:
    result = apply_change_diff("Hola mundo", before="xyz", after="abc")

    assert result is None


@pytest.mark.unit
def test_replace_with_multiline() -> None:
    markdown = "## Título\n\nContenido original aquí.\n\n## Otra sección"
    result = apply_change_diff(markdown, before="Contenido original aquí.", after="Contenido modificado.")

    assert result is not None
    assert "Contenido modificado." in result
    assert "Contenido original aquí." not in result
    assert "## Título" in result
    assert "## Otra sección" in result


@pytest.mark.unit
def test_merge_changes_with_diffs_propagates_change_class() -> None:
    # Arrange
    cosmetic = SectionChange(
        section="Visión",
        change_type=ChangeType.MODIFIED,
        change_class=ChangeClass.COSMETIC,
        before="Visión original.",
        after="Visión  original.",
    )

    # Act
    result = merge_changes_with_diffs([], [cosmetic])

    # Assert
    assert len(result) == 1
    assert result[0].change_class == "cosmetic"


@pytest.mark.unit
def test_append_to_empty_markdown() -> None:
    result = apply_change_diff("", before="", after="Nueva sección")

    assert result == "\n\nNueva sección"
