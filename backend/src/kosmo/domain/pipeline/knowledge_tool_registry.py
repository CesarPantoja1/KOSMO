from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class KnowledgeToolDef:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)  # type: ignore[reportUnknownVariableType]


KnowledgeToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


class KnowledgeToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, tuple[KnowledgeToolDef, KnowledgeToolHandler]] = {}

    def register(self, tool_def: KnowledgeToolDef, handler: KnowledgeToolHandler) -> None:
        self._tools[tool_def.name] = (tool_def, handler)

    def describe_for_llm(self) -> str:
        if not self._tools:
            return ""

        lines: list[str] = [
            "## Herramientas de conocimiento disponibles\n",
            "Puedes solicitar informacion adicional usando el formato:",
            '[TOOL: nombre] {"arg": "valor"}',
            "El sistema ejecutara la herramienta y te devolvera el resultado.\n",
        ]
        for tool_def, _handler in self._tools.values():
            params_desc = json.dumps(tool_def.parameters, ensure_ascii=False)
            lines.append(f"- **{tool_def.name}**: {tool_def.description}")
            lines.append(f"  Parametros: {params_desc}")
        return "\n".join(lines)

    async def execute(self, name: str, tool_input: dict[str, Any]) -> str | None:
        entry = self._tools.get(name)
        if entry is None:
            return None
        _tool_def, handler = entry
        try:
            return await handler(tool_input)
        except Exception as exc:
            return f"Error al ejecutar {name}: {exc}"

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())
