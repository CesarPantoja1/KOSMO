from __future__ import annotations

import pytest

from kosmo.domain.sdd.text_normalizer import strip_origin_line


@pytest.mark.unit
def test_strip_origin_line_quita_linea_final() -> None:
    # Arrange
    text = (
        "El repartidor del barrio marca el avance del pedido en cada etapa.\n"
        "Origen: Meta Gestion de pedidos en Metas del producto y Actor Repartidor en Actores."
    )

    # Act
    result = strip_origin_line(text)

    # Assert
    assert result == "El repartidor del barrio marca el avance del pedido en cada etapa."
    assert "Origen" not in result


@pytest.mark.unit
def test_strip_origin_line_quita_variante_bold() -> None:
    # Arrange
    text = "Descripción de la feature.\n\n**Origen:** Se deriva de la meta Reparto equitativo de gastos."

    # Act
    result = strip_origin_line(text)

    # Assert
    assert result == "Descripción de la feature."


@pytest.mark.unit
def test_strip_origin_line_quita_linea_en_blanco_previa() -> None:
    # Arrange
    text = "Descripción de la feature.\n\nOrigen: Meta Gestion en Metas del producto.\n"

    # Act
    result = strip_origin_line(text)

    # Assert
    assert result == "Descripción de la feature."


@pytest.mark.unit
def test_strip_origin_line_no_op_sin_origen() -> None:
    # Arrange
    text = "Descripción de la feature sin origen."

    # Act
    result = strip_origin_line(text)

    # Assert
    assert result == text


@pytest.mark.unit
def test_strip_origin_line_no_quita_origen_en_medio() -> None:
    # Arrange — "Origen:" en medio del texto no es la sección de origen
    text = "La feature menciona el origen del pedido.\nContinúa la descripción."

    # Act
    result = strip_origin_line(text)

    # Assert
    assert result == text
