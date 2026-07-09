from __future__ import annotations

from kosmo.contracts.pipeline.phase_outputs import ValidationResult


def validate_refine_input_exists(current_requirements_markdown: str | None) -> ValidationResult:
    """Verifica que existan requisitos de entrada para poder refinarlos."""
    if not current_requirements_markdown or not current_requirements_markdown.strip():
        return ValidationResult(
            is_valid=False,
            errors=["No existen requisitos de entrada para refinar. La característica debe tener requisitos previos."],
        )
    return ValidationResult(is_valid=True)
