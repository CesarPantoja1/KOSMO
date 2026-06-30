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


class ToolRegistry:
    """Registro de herramientas del agente que mapea nombres a callables."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolCallable] = {}

    def register(self, name: str, fn: ToolCallable) -> None:
        self._tools[name] = fn

    def execute(self, name: str, tool_input: Any) -> dict[str, Any]:
        if name not in self._tools:
            return {"error": f"Herramienta '{name}' no encontrada"}

        normalized = _format_tool_input(tool_input)
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
