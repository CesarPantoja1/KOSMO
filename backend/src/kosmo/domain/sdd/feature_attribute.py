from __future__ import annotations

from unicodedata import normalize


def feature_attribute(section: str) -> str | None:
    """Mapea el titulo de una seccion al atributo modificable de Feature."""
    normalized = "".join(char for char in normalize("NFKD", section).lower() if char.isalnum())
    if normalized in {"titulo", "titulodelacaracteristica"}:
        return "title"
    if normalized in {"descripcion", "descripciondelacaracteristica"}:
        return "description"
    if normalized in {"origen", "origendelacaracteristica"}:
        return "origin"
    return None
