from kosmo.contracts.pipeline.phase_outputs import ValidationResult


def validate_activity_diagram_syntax(diagram: str) -> ValidationResult:
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

    # Validar balance de if / endif
    if_count = sum(1 for line in lines if line.startswith("if ") or line.startswith("if("))
    endif_count = sum(1 for line in lines if line == "endif" or line == "end if")
    
    if if_count > endif_count:
        errors.append(
            f"Se detectaron condicionales 'if' sin su correspondiente 'endif' "
            f"({if_count} if vs {endif_count} endif)"
        )
    elif if_count < endif_count:
        errors.append(
            f"Se detectaron 'endif' sobrantes sin un 'if' correspondiente "
            f"({if_count} if vs {endif_count} endif)"
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

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )
