from __future__ import annotations

import pytest

from kosmo.domain.sdd.document_converters import slugify_spanish


@pytest.mark.unit
def test_slugify_removes_accents_and_special_characters() -> None:
    # Act
    slug = slugify_spanish("Proyecto con Çaráctères!@#$%")

    # Assert
    assert slug == "proyecto-con-caracteres"


@pytest.mark.unit
def test_slugify_maps_enye_to_plain_n() -> None:
    # Act
    slug = slugify_spanish("Niño pequeño")

    # Assert
    assert slug == "nino-pequeno"


@pytest.mark.unit
def test_slugify_strips_trailing_separators() -> None:
    # Act
    slug = slugify_spanish("Hola - ")

    # Assert
    assert slug == "hola"


@pytest.mark.unit
def test_slugify_returns_empty_string_for_punctuation_only() -> None:
    # Act
    slug = slugify_spanish("!!!...")

    # Assert
    assert slug == ""
