from __future__ import annotations

from typing import Any

from kosmo.contracts.pipeline.phase_outputs import ValidationResult


def validate_refine_input_exists(current_requirements: list[Any]) -> ValidationResult:
    """Verifica que existan requisitos de entrada para poder refinarlos."""
    if not current_requirements or len(current_requirements) == 0:
        return ValidationResult(
            is_valid=False,
            errors=["No existen requisitos de entrada para refinar. La característica debe tener requisitos previos."],
        )
    return ValidationResult(is_valid=True)
