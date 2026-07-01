from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition

ToolCallable = Callable[[dict[str, Any]], dict[str, Any]]


def _format_tool_input(tool_input: Any) -> dict[str, Any]:
    if isinstance(tool_input, str):
        try:
            return json.loads(tool_input)  # type: ignore[reportUnknownArgumentType]
        except (json.JSONDecodeError, TypeError):
            return {"text": tool_input}  # type: ignore[reportUnknownArgumentType]
    if isinstance(tool_input, dict):
        return tool_input  # type: ignore[reportUnknownVariableType]
    return {"value": tool_input}  # type: ignore[reportUnknownArgumentType]


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    return True


class ToolRegistry:
    """Registro de herramientas del agente que mapea nombres a callables.

    Soporta registro simple (solo callable) y registro con definicion
    que habilita validacion de parametros contra un JSON schema.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolCallable] = {}
        self._definitions: dict[str, ToolDefinition] = {}

    def register(self, name: str, fn: ToolCallable) -> None:
        self._tools[name] = fn

    def register_with_definition(
        self,
        name: str,
        fn: ToolCallable,
        definition: ToolDefinition,
    ) -> None:
        self._tools[name] = fn
        self._definitions[name] = definition

    def execute(self, name: str, tool_input: Any) -> dict[str, Any]:
        if name not in self._tools:
            return {"error": f"Herramienta '{name}' no encontrada"}

        normalized = _format_tool_input(tool_input)

        definition = self._definitions.get(name)
        if definition is not None and definition.parameters:
            validation_error = self._validate_parameters(
                normalized,
                definition.parameters,
            )
            if validation_error is not None:
                return {"error": validation_error}

        try:
            return self._tools[name](normalized)
        except Exception as exc:
            return {"error": str(exc)}

    def describe_tools(self, definitions: list[ToolDefinition]) -> str:
        if not definitions:
            return "No hay herramientas disponibles."

        lines: list[str] = []
        for td in definitions:
            name = td.name
            desc = td.description
            registered = " [disponible]" if name in self._tools else " [no implementada]"
            lines.append(f"- {name}: {desc}{registered}")
        return "\n".join(lines)

    @staticmethod
    def _validate_parameters(
        input_data: dict[str, Any],
        schema: dict[str, Any],
    ) -> str | None:
        properties = schema.get("properties", {})
        required: list[str] = schema.get("required", [])

        for param in required:
            if param not in input_data:
                return (
                    f"Parametro requerido '{param}' no proporcionado. "
                    f"Se requieren: {', '.join(required)}"
                )

        for param, value in input_data.items():
            if param not in properties:
                continue
            expected_type = properties[param].get("type", "string")
            if not _matches_type(value, expected_type):
                return (
                    f"Parametro '{param}' debe ser de tipo '{expected_type}' "
                    f"pero se recibio '{type(value).__name__}'"
                )

        return None
