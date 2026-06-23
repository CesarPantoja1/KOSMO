from __future__ import annotations

import re
import unicodedata
from typing import Any, cast

from kosmo.contracts.pipeline.phase_outputs import ValidationResult
from kosmo.domain.sdd.output_guardrails import detect_technical_terms


def _normalize_text(text: str) -> set[str]:
    """Normaliza texto en español (minúsculas, sin acentos, sin puntuación y sin stopwords)."""
    text = text.lower()
    # Eliminar acentos/tildes
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    # Eliminar puntuación
    text = re.sub(r"[^\w\s]", " ", text)
    # Tokenizar y filtrar stopwords comunes en español
    words = text.split()
    stopwords = {
        "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al", "y", "o", "e",
        "u", "en", "para", "por", "con", "sin", "sobre", "tras", "desde", "hasta", "que", "es",
        "son", "este", "esta", "estos", "estas", "como", "quiero", "sistema", "usuario",
        "permite", "debe", "poder", "funcionalidad", "caracteristica", "proyecto",
    }
    return {w for w in words if len(w) > 2 and w not in stopwords}


def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Calcula la similitud de Jaccard entre dos conjuntos de palabras."""
    if not set_a or not set_b:
        return 0.0
    return len(set_a.intersection(set_b)) / len(set_a.union(set_b))


def validate_feature_structure(features: Any) -> ValidationResult:
    """Verifica que las características generadas tengan la estructura correcta.

    Cada característica debe tener:
    - number (int)
    - title (str, no vacío, longitud mín 3)
    - description (str, no vacío, longitud mín 20)
    - rationale (str, no vacío, longitud mín 15)
    - inferred_from (list[str], no vacío)

    Además, verifica que no contengan términos técnicos/detalles de implementación.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(features, list):
        return ValidationResult(
            is_valid=False,
            errors=["Las características deben presentarse en una lista."],
        )

    if not features:
        return ValidationResult(
            is_valid=False,
            errors=["La lista de características está vacía."],
        )

    for idx, raw_feat in enumerate(cast(list[object], features)):
        if not isinstance(raw_feat, dict):
            errors.append(f"El elemento en el índice {idx} no es un objeto válido.")
            continue

        # Copiar a un diccionario con tipos explícitos para Pyright
        feat: dict[str, Any] = {}
        for k, v in cast(dict[object, object], raw_feat).items():
            if isinstance(k, str):
                feat[k] = v

        title = str(feat.get("title", f"Característica {idx + 1}"))
        # 1. Verificar campos requeridos
        for field in ["number", "title", "description", "rationale", "inferred_from"]:
            if field not in feat:
                errors.append(
                    f"Característica '{title}' (índice {idx}) no tiene el campo "
                    f"requerido '{field}'."
                )

        # Si hay errores críticos de estructura, saltar validación detallada de este elemento
        if any(
            f not in feat
            for f in ["number", "title", "description", "rationale", "inferred_from"]
        ):
            continue

        number = feat["number"]
        title_val = feat["title"]
        desc_val = feat["description"]
        rationale_val = feat["rationale"]
        inferred_val = feat["inferred_from"]

        # 2. Validar tipos de datos y contenidos mínimos
        if not isinstance(number, int):
            errors.append(
                f"El campo 'number' en la característica '{title}' debe ser un número entero."
            )

        if not isinstance(title_val, str) or not title_val.strip():
            errors.append(
                f"El campo 'title' en la característica {idx + 1} debe ser un texto no vacío."
            )
        elif len(title_val.strip()) < 3:
            errors.append(f"El título '{title_val}' es demasiado corto (mínimo 3 caracteres).")

        if not isinstance(desc_val, str) or not desc_val.strip():
            errors.append(
                f"La descripción en la característica '{title}' debe ser un texto no vacío."
            )
        elif len(desc_val.strip()) < 20:
            errors.append(
                f"La descripción de '{title}' es demasiado corta (mínimo 20 caracteres)."
            )

        if not isinstance(rationale_val, str) or not rationale_val.strip():
            errors.append(
                f"La justificación ('rationale') en la característica '{title}' debe "
                f"ser un texto no vacío."
            )
        elif len(rationale_val.strip()) < 15:
            errors.append(
                f"La justificación de '{title}' es demasiado corta (mínimo 15 caracteres)."
            )

        if not isinstance(inferred_val, list):
            errors.append(
                f"El campo 'inferred_from' en la característica '{title}' debe ser "
                f"una lista de textos."
            )
        elif not inferred_val:
            errors.append(
                f"El campo 'inferred_from' en la característica '{title}' no puede estar vacío."
            )
        else:
            for item_idx, raw_item in enumerate(cast(list[object], inferred_val)):
                if not isinstance(raw_item, str):
                    errors.append(
                        f"El ítem {item_idx} de 'inferred_from' en la característica "
                        f"'{title}' debe ser un texto válido."
                    )
                    continue
                item: str = raw_item
                if not item.strip():
                    errors.append(
                        f"El ítem {item_idx} de 'inferred_from' en la característica "
                        f"'{title}' no puede estar en blanco."
                    )

        # 3. Detectar fugas de implementación (términos técnicos prohibidos)
        for field_name, field_val in [
            ("title", title_val),
            ("description", desc_val),
            ("rationale", rationale_val),
        ]:
            if isinstance(field_val, str):
                tech_result = detect_technical_terms(
                    field_val, section=f"característica '{title}' ({field_name})"
                )
                if not tech_result.is_valid:
                    for violation in tech_result.violations:
                        errors.append(
                            f"Término técnico prohibido '{violation.term}' encontrado en "
                            f"{violation.section}: {violation.context}"
                        )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_feature_uniqueness(
    features: Any,
    existing_titles: list[str] | None = None,
) -> ValidationResult:
    """Verifica que no haya redundancia semántica entre las características generadas

    ni con las existentes.

    Compara:
    - Títulos de características generadas entre sí (Similitud Jaccard > 0.4 es error).
    - Descripciones de características generadas entre sí (Similitud Jaccard > 0.5 es error).
    - Títulos de características generadas contra existentes (Similitud Jaccard > 0.4 es error).
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(features, list) or not features:
        return ValidationResult(is_valid=True)

    # 1. Comparar generadas entre sí
    normalized_titles: list[tuple[str, set[str]]] = []
    normalized_descs: list[tuple[str, set[str]]] = []

    for raw_feat in cast(list[object], features):
        if isinstance(raw_feat, dict):
            feat: dict[str, Any] = {}
            for k, v in cast(dict[object, object], raw_feat).items():
                if isinstance(k, str):
                    feat[k] = v

            title = feat.get("title")
            desc = feat.get("description")
            if isinstance(title, str) and isinstance(desc, str):
                normalized_titles.append((title, _normalize_text(title)))
                normalized_descs.append((title, _normalize_text(desc)))

    n = len(normalized_titles)
    for i in range(n):
        title_i, title_words_i = normalized_titles[i]
        _, desc_words_i = normalized_descs[i]

        for j in range(i + 1, n):
            title_j, title_words_j = normalized_titles[j]
            _, desc_words_j = normalized_descs[j]

            # Similitud en títulos
            title_sim = _jaccard_similarity(title_words_i, title_words_j)
            if title_sim > 0.4:
                errors.append(
                    f"Redundancia semántica detectada: los títulos de '{title_i}' y "
                    f"'{title_j}' son demasiado similares (similitud {title_sim:.2f})."
                )

            # Similitud en descripciones
            desc_sim = _jaccard_similarity(desc_words_i, desc_words_j)
            if desc_sim > 0.5:
                errors.append(
                    f"Redundancia semántica detectada: las descripciones de '{title_i}' "
                    f"y '{title_j}' son demasiado similares (similitud {desc_sim:.2f})."
                )

    # 2. Comparar generadas contra existentes
    if existing_titles:
        normalized_existing = [
            (t, _normalize_text(t)) for t in existing_titles
        ]
        for title_gen, gen_words in normalized_titles:
            for title_exist, exist_words in normalized_existing:
                sim = _jaccard_similarity(gen_words, exist_words)
                if sim > 0.4:
                    errors.append(
                        f"Redundancia semántica detectada: la característica generada "
                        f"'{title_gen}' ya existe o es muy similar a la característica "
                        f"existente '{title_exist}' (similitud {sim:.2f})."
                    )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
