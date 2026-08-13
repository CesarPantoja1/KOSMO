from __future__ import annotations

import pytest

from kosmo.domain.sdd.feature_attribute import feature_attribute


@pytest.mark.unit
def test_feature_attribute_maps_title_sections() -> None:
    # Act
    attribute = feature_attribute("Título")

    # Assert
    assert attribute == "title"


@pytest.mark.unit
def test_feature_attribute_maps_title_of_feature_sections() -> None:
    # Act
    attribute = feature_attribute("Título de la característica")

    # Assert
    assert attribute == "title"


@pytest.mark.unit
def test_feature_attribute_maps_description_sections_ignoring_accents() -> None:
    # Act
    attribute = feature_attribute("Descripción de la característica")

    # Assert
    assert attribute == "description"


@pytest.mark.unit
def test_feature_attribute_maps_origin_sections() -> None:
    # Act
    attribute = feature_attribute("Origen de la característica")

    # Assert
    assert attribute == "origin"


@pytest.mark.unit
def test_feature_attribute_returns_none_for_unknown_section() -> None:
    # Act
    attribute = feature_attribute("Historial de cambios")

    # Assert
    assert attribute is None
