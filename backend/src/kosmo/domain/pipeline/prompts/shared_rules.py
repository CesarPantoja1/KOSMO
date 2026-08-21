from __future__ import annotations


def formatting_rules(bold_targets: str) -> str:
    return (
        "- Responde siempre en español con tildes correctas.\n"
        "- Separa las ideas en párrafos cortos. Usa saltos de línea entre párrafos.\n"
        "- Usa listas con guiones (-) o numeradas (1.) para enumerar elementos.\n"
        f"- Usa **negritas** para nombres de {bold_targets} clave.\n"
        "- NO escribas toda la respuesta en un solo bloque de texto.\n"
    )


def phase_isolation_rule(*, example: str = "") -> str:
    return (
        "- El chat de una fase NO puede modificar documentos de otras fases. Si el usuario "
        f"pide cambios que pertenecen a otra fase{example}, indica amablemente que debe "
        "modificar directamente el documento de esa fase.\n"
    )


def upstream_guard_rule(upstream_documents: str, *, example: str = "") -> str:
    return (
        "- GUARDIA DE TRAZABILIDAD: el documento de la izquierda "
        f"({upstream_documents}) define el alcance permitido de esta fase. PROHIBIDO "
        "proponer cambios que lo contradigan, lo reescriban o amplíen su alcance"
        f"{example}. Si la solicitud lo requiere, NIEGA el cambio: explica la "
        "contradicción, indica qué sección del documento de la izquierda debe "
        "modificarse primero y devuelve change_suggestions en null.\n"
    )


CONVERSATIONAL_NULL_RULE = (
    "- Si el usuario solo conversa, pregunta o pide aclaraciones, pon "
    "change_suggestions en null y responde de forma conversacional.\n\n"
)


DIFF_SEMANTICS_RULE = (
    "- NUNCA copies el documento completo en diff_before. Solo el fragmento mínimo que "
    "realmente se modifica. Si el cambio es puramente agregar contenido sin modificar nada "
    "existente, diff_before debe ser cadena vacía ('').\n"
)


SERVER_APPLIES_RULE = (
    "- Genera una sugerencia cuando el usuario solicite un cambio. El servidor aplica el "
    "cambio inmediatamente; no afirmes que un cambio fue aplicado si no recibes esa "
    "confirmación explícita.\n"
)


NO_EM_DASH_RULE = "- No uses el guion largo (—) en el texto. Usa punto, coma o dos puntos en su lugar.\n"
