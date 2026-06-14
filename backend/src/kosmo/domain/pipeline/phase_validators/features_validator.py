from __future__ import annotations

from kosmo.contracts.pipeline.phase_outputs import ValidationResult
from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.contracts.sdd.feature import Feature


def validate_features_structure(features: list[Feature]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    for feature in features:
        words_in_title = len(feature.title.split())
        if words_in_title > 6:
            errors.append(
                f"{feature.display_id}: Titulo '{feature.title}' tiene {words_in_title} palabras "
                f"(maximo 6)"
            )

        if not feature.description.strip():
            errors.append(f"{feature.display_id}: Descripcion vacia")
        else:
            description_lower = feature.description.lower()
            has_what = any(
                w in description_lower
                for w in ["que hace", "que permite", "permite", "gestiona", "administra"]
            )
            has_who = any(
                w in description_lower
                for w in ["para quien", "usuario", "actor", "cliente", "administrador"]
            )
            if not has_what:
                warnings.append(
                    f"{feature.display_id}: Descripcion no incluye QUÉ hace la caracteristica"
                )
            if not has_who:
                warnings.append(
                    f"{feature.display_id}: Descripcion no incluye PARA QUIÉN esta destinada"
                )

        if not feature.rationale.strip():
            warnings.append(f"{feature.display_id}: Sin rationale")

    if len(features) < 3:
        warnings.append(f"Se recomiendan al menos 3 features, solo hay {len(features)}")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_features_semantic(
    features: list[Feature],
    discovery: RichTextDocument | None = None,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    titles_lower: list[str] = []
    for feature in features:
        titles_lower.append(feature.title.lower())

    for i in range(len(titles_lower)):
        for j in range(i + 1, len(titles_lower)):
            words_i = set(titles_lower[i].split())
            words_j = set(titles_lower[j].split())
            overlap = len(words_i & words_j)
            if overlap > 2:
                warnings.append(
                    f"Posible solapamiento: '{features[i].title}' y '{features[j].title}' "
                    f"comparten {overlap} palabras"
                )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
