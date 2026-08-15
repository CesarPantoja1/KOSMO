from kosmo.contracts.pipeline.phase_outputs import ValidationResult

_DEFAULT_MAX_ACTION_NODES = 20
_DEFAULT_MAX_SWIMLANES = 4
_DEFAULT_MAX_NESTING_DEPTH = 3


def _count_action_nodes(lines: list[str]) -> int:
    return sum(1 for line in lines if line.startswith(":") and ";" in line)


def _count_swimlanes(lines: list[str]) -> int:
    return sum(1 for line in lines if line.startswith("|") and line.endswith("|"))


def _max_nesting_depth(lines: list[str]) -> int:
    depth = 0
    max_depth = 0
    for line in lines:
        if line.startswith("if ") or line.startswith("if("):
            depth += 1
            max_depth = max(max_depth, depth)
        elif line == "endif" or line == "end if":
            depth -= 1
        elif line == "fork":
            depth += 1
            max_depth = max(max_depth, depth)
        elif line == "end merge" or line == "endmerge":
            depth -= 1
    return max_depth


def validate_activity_diagram_syntax(
    diagram: str,
    *,
    max_action_nodes: int = _DEFAULT_MAX_ACTION_NODES,
    max_swimlanes: int = _DEFAULT_MAX_SWIMLANES,
    max_nesting_depth: int = _DEFAULT_MAX_NESTING_DEPTH,
) -> ValidationResult:
    """Valida la sintaxis y estructura de un diagrama PlantUML (Activity Diagram)."""
    errors: list[str] = []
    warnings: list[str] = []

    diagram = diagram.strip()

    if not diagram.startswith("@startuml"):
        errors.append("El diagrama debe comenzar con @startuml")

    if not diagram.endswith("@enduml"):
        errors.append("El diagrama debe terminar con @enduml")

    # Separar en líneas eliminando espacios innecesarios
    lines = [line.strip() for line in diagram.split("\n")]
    has_start = any(line == "start" for line in lines)
    has_stop = any(line in ("stop", "end") for line in lines)

    if not has_start:
        warnings.append("Es recomendable incluir un nodo inicial 'start'")

    if not has_stop:
        warnings.append("Es recomendable incluir un nodo final 'stop' o 'end'")

    # Validar presencia de carriles / swimlanes (|NombreCarril|)
    has_swimlanes = any(line.startswith("|") and line.endswith("|") for line in lines)
    if not has_swimlanes:
        warnings.append("Es recomendable organizar las actividades utilizando carriles/swimlanes (|NombreCarril|)")

    # Métricas de complejidad: warnings informativos para guiar la simplificacion
    action_nodes = _count_action_nodes(lines)
    if action_nodes > max_action_nodes:
        warnings.append(
            f"El diagrama contiene {action_nodes} nodos de acción (máximo recomendado: {max_action_nodes})."
        )

    swimlanes = _count_swimlanes(lines)
    if swimlanes > max_swimlanes:
        warnings.append(f"El diagrama contiene {swimlanes} carriles (máximo recomendado: {max_swimlanes}).")

    nesting_depth = _max_nesting_depth(lines)
    if nesting_depth > max_nesting_depth:
        warnings.append(
            f"El diagrama tiene un anidamiento máximo de {nesting_depth} niveles "
            f"(máximo recomendado: {max_nesting_depth})."
        )

    # Validar balance de if / endif
    if_count = sum(1 for line in lines if line.startswith("if ") or line.startswith("if("))
    endif_count = sum(1 for line in lines if line == "endif" or line == "end if")

    if if_count > endif_count:
        errors.append(
            f"Se detectaron condicionales 'if' sin su correspondiente 'endif' ({if_count} if vs {endif_count} endif)"
        )
    elif if_count < endif_count:
        errors.append(
            f"Se detectaron 'endif' sobrantes sin un 'if' correspondiente ({if_count} if vs {endif_count} endif)"
        )

    # Validar balance de fork / end merge (concurrencia)
    fork_count = sum(1 for line in lines if line == "fork")
    endmerge_count = sum(1 for line in lines if line == "end merge" or line == "endmerge")

    if fork_count > endmerge_count:
        errors.append(
            f"Se detectaron ramas concurrentes 'fork' sin su correspondiente 'end merge' "
            f"({fork_count} fork vs {endmerge_count} end merge)"
        )
    elif fork_count < endmerge_count:
        errors.append(
            f"Se detectaron 'end merge' sobrantes sin un 'fork' correspondiente "
            f"({fork_count} fork vs {endmerge_count} end merge)"
        )

    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
