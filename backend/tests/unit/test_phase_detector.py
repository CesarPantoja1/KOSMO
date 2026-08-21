from __future__ import annotations

import pytest

from kosmo.domain.pipeline.phase_detector import detect_phase_mismatch, phase_label


@pytest.mark.unit
def test_detect_returns_requisitos_when_content_matches_ears_keywords() -> None:
    # Act
    target = detect_phase_mismatch(
        "Agrega un criterio de aceptación con dado-cuando-entonces",
        "caracteristicas",
    )

    # Assert
    assert target == "requisitos"


@pytest.mark.unit
def test_detect_returns_none_when_detected_phase_matches_current() -> None:
    # Act
    target = detect_phase_mismatch("Quiero cambiar la visión del negocio", "descubrimiento")

    # Assert
    assert target is None


@pytest.mark.unit
def test_detect_returns_none_when_current_phase_scores_two_or_more() -> None:
    # Arrange: 2 keywords de caracteristicas y 3 de requisitos
    content = "la característica y su funcionalidad; el requisito con criterio de aceptación en ears"

    # Act
    target = detect_phase_mismatch(content, "caracteristicas")

    # Assert
    assert target is None


@pytest.mark.unit
def test_detect_returns_none_for_content_without_keywords() -> None:
    # Act
    target = detect_phase_mismatch("ayúdame a entender qué sigue", "caracteristicas")

    # Assert
    assert target is None


@pytest.mark.unit
def test_detect_returns_none_for_empty_content() -> None:
    # Act
    target = detect_phase_mismatch("   ", "caracteristicas")

    # Assert
    assert target is None


@pytest.mark.unit
def test_phase_label_returns_human_readable_label() -> None:
    # Act
    label = phase_label("requisitos")

    # Assert
    assert label == "Requisitos"


@pytest.mark.unit
def test_phase_label_falls_back_to_key_for_unknown_phase() -> None:
    # Act
    label = phase_label("fase_desconocida")

    # Assert
    assert label == "fase_desconocida"
