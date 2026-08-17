from __future__ import annotations

_PHASE_KEYWORDS: dict[str, list[str]] = {
    "descubrimiento": [
        "visión",
        "vision",
        "negocio",
        "mercado",
        "propuesta de valor",
        "alcance general",
        "actores",
        "actores del sistema",
        "metas",
        "meta del producto",
        "problema",
        "diferenciador",
        "modelo de negocio",
        "estrategia",
        "objetivo general",
        "público objetivo",
        "publico objetivo",
        "segmento de clientes",
    ],
    "caracteristicas": [
        "característica",
        "caracteristica",
        "funcionalidad",
        "feature",
        "título",
        "titulo",
        "origen de la característica",
        "c01",
        "c02",
        "c03",
        "c04",
        "c05",
        "acción de usuario",
        "accion de usuario",
        "regla de negocio",
        "descuento",
    ],
    "requisitos": [
        "requisito",
        "criterio de aceptación",
        "criterio de aceptacion",
        "dado-cuando-entonces",
        "ears",
        "validación",
        "validacion",
        "especificación técnica",
        "especificacion tecnica",
        "req-",
        "req_",
        "given-when-then",
        "gwt",
    ],
}

_PHASE_LABELS: dict[str, str] = {
    "descubrimiento": "Descubrimiento",
    "caracteristicas": "Características",
    "requisitos": "Requisitos",
}


def detect_phase_mismatch(content: str, current_phase: str) -> str | None:
    """Devuelve la fase detectada si difiere de la actual; None si el contexto es valido.

    La regla de desempate: si la fase actual acumula 2 o mas keywords, el
    contenido se considera propio de la fase actual aunque otra fase puntue mas.
    """
    content = content.strip().lower()
    if not content:
        return None

    current = current_phase.lower()

    scores: dict[str, int] = {}
    for phase, keywords in _PHASE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in content)
        if score > 0:
            scores[phase] = score

    if not scores:
        return None

    best_phase = max(scores, key=lambda k: scores[k])
    if best_phase == current:
        return None

    if scores.get(current, 0) >= 2:
        return None

    return best_phase


def phase_label(phase_key: str) -> str:
    return _PHASE_LABELS.get(phase_key, phase_key)
