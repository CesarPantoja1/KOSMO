from kosmo.contracts.pipeline.phase_outputs import ValidationResult


def validate_plantuml_syntax(diagram: str) -> ValidationResult:
    """Valida la sintaxis básica de un diagrama PlantUML."""
    errors: list[str] = []
    warnings: list[str] = []

    diagram = diagram.strip()

    if not diagram.startswith("@startuml"):
        errors.append("El diagrama debe comenzar con @startuml")
    
    if not diagram.endswith("@enduml"):
        errors.append("El diagrama debe terminar con @enduml")

    # Reglas específicas de diagramas de actividad
    lines = diagram.split("\n")
    has_start = any(line.strip() == "start" for line in lines)
    has_stop = any(line.strip() in ("stop", "end") for line in lines)

    if not has_start:
        warnings.append("Es recomendable incluir un nodo inicial 'start'")
    
    if not has_stop:
        warnings.append("Es recomendable incluir un nodo final 'stop' o 'end'")

    if ("if (" in diagram or "if " in diagram) and ("endif" not in diagram and "end if" not in diagram):
        errors.append("Se detectó una condición 'if' sin su correspondiente 'endif'")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )
