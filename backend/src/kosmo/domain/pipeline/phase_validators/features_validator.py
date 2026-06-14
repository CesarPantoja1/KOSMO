from __future__ import annotations

from typing import Any

from kosmo.contracts.pipeline.phase_outputs import ValidationResult
from kosmo.contracts.sdd.document import RichTextDocument


def _get(feature: Any, key: str, default: Any = "") -> Any:
    if isinstance(feature, dict):
        return feature.get(key, default)
    return getattr(feature, key, default)


def _get_title(feature: Any) -> str:
    return str(_get(feature, "title", ""))


def _get_description(feature: Any) -> str:
    return str(_get(feature, "description", ""))


def _get_rationale(feature: Any) -> str:
    return str(_get(feature, "rationale", ""))


def _get_display_id(feature: Any) -> str:
    if isinstance(feature, dict):
        number = feature.get("number", 0)
        return f"C{number:02d}"
    return str(_get(feature, "display_id", "C??"))


def validate_features_structure(features: list[Any]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    for feature in features:
        title = _get_title(feature)
        display_id = _get_display_id(feature)
        description = _get_description(feature)
        rationale = _get_rationale(feature)

        words_in_title = len(title.split())
        if words_in_title > 6:
            errors.append(
                f"{display_id}: Título '{title}' tiene {words_in_title} palabras "
                f"(máximo 6)"
            )

        if not description.strip():
            errors.append(f"{display_id}: Descripción vacía")

        if not rationale.strip():
            warnings.append(f"{display_id}: Sin rationale")

    if len(features) < 3:
        warnings.append(f"Se recomiendan al menos 3 features, solo hay {len(features)}")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_features_semantic(
    features: list[Any],
    discovery: RichTextDocument | None = None,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    titles_lower: list[str] = []
    for feature in features:
        titles_lower.append(_get_title(feature).lower())

    for i in range(len(titles_lower)):
        for j in range(i + 1, len(titles_lower)):
            words_i = set(titles_lower[i].split())
            words_j = set(titles_lower[j].split())
            overlap = len(words_i & words_j)
            if overlap > 2:
                warnings.append(
                    f"Posible solapamiento: '{_get_title(features[i])}' y "
                    f"'{_get_title(features[j])}' comparten {overlap} palabras"
                )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
