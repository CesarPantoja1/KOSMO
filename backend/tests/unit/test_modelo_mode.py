from __future__ import annotations

import pytest

from kosmo.domain.pipeline.phase_modes.modelo_mode import ModeloMode


@pytest.mark.unit
def test_modelo_prompt_includes_complexity_limits() -> None:
    # Arrange
    mode = ModeloMode()

    # Act
    prompt = mode.system_prompt

    # Assert
    assert "20 nodos" in prompt
    assert "4 carriles" in prompt
    assert "Happy Path" in prompt


@pytest.mark.unit
def test_modelo_prompt_includes_simplification_strategy() -> None:
    # Arrange
    mode = ModeloMode()

    # Act
    prompt = mode.system_prompt

    # Assert
    assert "8 requisitos" in prompt
    assert "criterios de aceptación" in prompt
    assert "agrupa" in prompt
