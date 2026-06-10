from kosmo.contracts.memory.user_preference import UserPreference


def injection_preparer(preferences: list[UserPreference]) -> str:
    if not preferences:
        return ""

    lines = ["## Preferencias del Usuario (aprendidas de correcciones anteriores)"]
    for i, pref in enumerate(preferences, 1):
        lines.append(f"{i}. {pref.rule_text}")

    lines.append("")
    lines.append(
        "Aplica estas preferencias al generar contenido. "
        "Si dos preferencias entran en conflicto, prioriza la mas reciente."
    )

    return "\n".join(lines)
