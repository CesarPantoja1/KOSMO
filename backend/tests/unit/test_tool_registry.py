import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.domain.pipeline.tool_registry import ToolRegistry


@pytest.mark.unit
def test_tool_registry_register_and_execute() -> None:
    # Arrange
    registry = ToolRegistry()
    registry.register("echo", lambda inp: {"result": inp.get("text", "")})

    # Act
    result = registry.execute("echo", {"text": "hola"})

    # Assert
    assert result == {"result": "hola"}


@pytest.mark.unit
def test_tool_registry_execute_raises_when_tool_not_found() -> None:
    # Arrange
    registry = ToolRegistry()

    # Act
    result = registry.execute("nonexistent", {})

    # Assert
    assert "error" in result
    assert "no encontrada" in result["error"]


@pytest.mark.unit
def test_tool_registry_execute_returns_error_on_exception() -> None:
    # Arrange
    registry = ToolRegistry()
    registry.register("failing", lambda _: exec("raise ValueError('boom')"))  # noqa: S102

    # Act
    result = registry.execute("failing", {})

    # Assert
    assert "error" in result


@pytest.mark.unit
def test_tool_registry_execute_parses_json_string_input() -> None:
    # Arrange
    registry = ToolRegistry()
    registry.register("echo", lambda inp: {"parsed": inp})

    # Act
    result = registry.execute("echo", '{"key": "value"}')

    # Assert
    assert result["parsed"] == {"key": "value"}


@pytest.mark.unit
def test_tool_registry_execute_handles_non_dict_non_json_input() -> None:
    # Arrange
    registry = ToolRegistry()
    registry.register("echo", lambda inp: {"received": inp})

    # Act
    result = registry.execute("echo", 42)

    # Assert
    assert result["received"] == {"value": 42}


@pytest.mark.unit
def test_tool_registry_describe_tools_formats_definitions() -> None:
    # Arrange
    registry = ToolRegistry()
    registry.register("alpha", lambda _: {})

    # Act
    description = registry.describe_tools(
        [
            ToolDefinition(name="alpha", description="Primera herramienta"),
            ToolDefinition(name="beta", description="Segunda herramienta"),
        ]
    )

    # Assert
    assert "alpha" in description
    assert "Primera herramienta" in description
    assert "beta" in description
    assert "Segunda herramienta" in description
    assert "disponible" in description
    assert "no implementada" in description


@pytest.mark.unit
def test_tool_registry_describe_tools_handles_empty_list() -> None:
    # Arrange
    registry = ToolRegistry()

    # Act
    description = registry.describe_tools([])

    # Assert
    assert "No hay herramientas" in description
