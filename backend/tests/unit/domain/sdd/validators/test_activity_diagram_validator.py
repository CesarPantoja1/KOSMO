from kosmo.domain.sdd.validators.activity_diagram_validator import validate_activity_diagram_syntax


def test_validate_valid_diagram():
    diagram = """
    @startuml
    |#pink|Usuario|
    start
    :Recibir solicitud;
    |#lightgray|Sistema|
    if (¿Válido?) then (sí)
      :Procesar;
    else (no)
      :Rechazar;
    endif
    fork
      :Enviar email;
    fork again
      :Guardar en DB;
    end merge
    stop
    @enduml
    """
    result = validate_activity_diagram_syntax(diagram)
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert len(result.warnings) == 0


def test_validate_missing_startuml_enduml():
    diagram = """
    start
    :Hacer algo;
    stop
    """
    result = validate_activity_diagram_syntax(diagram)
    assert result.is_valid is False
    assert "El diagrama debe comenzar con @startuml" in result.errors
    assert "El diagrama debe terminar con @enduml" in result.errors


def test_validate_missing_start_stop():
    diagram = """
    @startuml
    :Hacer algo;
    @enduml
    """
    result = validate_activity_diagram_syntax(diagram)
    assert result.is_valid is True  # Es advertencia, no error
    assert any("start" in w for w in result.warnings)
    assert any("stop" in w for w in result.warnings)


def test_validate_unbalanced_if():
    diagram = """
    @startuml
    start
    if (¿Condición?) then (sí)
      :Hacer algo;
    stop
    @enduml
    """
    result = validate_activity_diagram_syntax(diagram)
    assert result.is_valid is False
    assert any("condicionales 'if' sin su correspondiente 'endif'" in e for e in result.errors)


def test_validate_unbalanced_endif():
    diagram = """
    @startuml
    start
    :Hacer algo;
    endif
    stop
    @enduml
    """
    result = validate_activity_diagram_syntax(diagram)
    assert result.is_valid is False
    assert any("'endif' sobrantes sin un 'if' correspondiente" in e for e in result.errors)


def test_validate_unbalanced_fork():
    diagram = """
    @startuml
    start
    fork
      :Hacer A;
    fork again
      :Hacer B;
    stop
    @enduml
    """
    result = validate_activity_diagram_syntax(diagram)
    assert result.is_valid is False
    assert any("ramas concurrentes 'fork' sin su correspondiente 'end merge'" in e for e in result.errors)
