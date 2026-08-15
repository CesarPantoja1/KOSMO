import pytest

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


@pytest.mark.unit
def test_validate_diagram_within_complexity_limits_has_no_warnings() -> None:
    # Arrange: 20 nodos, 4 carriles, anidamiento de nivel 3
    diagram = "@startuml\n"
    diagram += "\n".join(f"|Carril{i}|" for i in range(4)) + "\n"
    diagram += "start\n"
    diagram += "if (¿A?) then (sí)\nif (¿B?) then (sí)\nif (¿C?) then (sí)\n"
    diagram += ":Paso;\nendif\nendif\nendif\n"
    diagram += "\n".join(f":Paso {i};" for i in range(19)) + "\n"
    diagram += "stop\n@enduml"

    # Act
    result = validate_activity_diagram_syntax(diagram)

    # Assert
    assert result.is_valid is True
    assert result.warnings == []


@pytest.mark.unit
def test_validate_too_many_action_nodes_warns() -> None:
    # Arrange
    diagram = "@startuml\n|C1|\nstart\n" + (":Paso;\n" * 25) + "stop\n@enduml"

    # Act
    result = validate_activity_diagram_syntax(diagram)

    # Assert
    assert result.is_valid is True
    assert any("25 nodos de acción" in w for w in result.warnings)


@pytest.mark.unit
def test_validate_too_many_swimlanes_warns() -> None:
    # Arrange
    diagram = "@startuml\n" + "\n".join(f"|Carril{i}|" for i in range(5)) + "\nstart\n:Paso;\nstop\n@enduml"

    # Act
    result = validate_activity_diagram_syntax(diagram)

    # Assert
    assert result.is_valid is True
    assert any("5 carriles" in w for w in result.warnings)


@pytest.mark.unit
def test_validate_deep_nesting_warns() -> None:
    # Arrange: 4 niveles de if anidados
    diagram = "@startuml\n|C1|\nstart\n"
    diagram += "if (¿A?) then (sí)\n" * 4
    diagram += ":Paso;\n"
    diagram += "endif\n" * 4
    diagram += "stop\n@enduml"

    # Act
    result = validate_activity_diagram_syntax(diagram)

    # Assert
    assert result.is_valid is True
    assert any("anidamiento máximo de 4 niveles" in w for w in result.warnings)


@pytest.mark.unit
def test_validate_complexity_thresholds_configurable() -> None:
    # Arrange: 25 nodos con umbral elevado a 30 no genera warning
    diagram = "@startuml\n|C1|\nstart\n" + (":Paso;\n" * 25) + "stop\n@enduml"

    # Act
    result = validate_activity_diagram_syntax(diagram, max_action_nodes=30)

    # Assert
    assert result.is_valid is True
    assert not any("nodos de acción" in w for w in result.warnings)
