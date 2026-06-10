from __future__ import annotations

import time

from kosmo.contracts.orchestration.tools import (
    ToolDefinition,
    ToolHandler,
    ToolResult,
)


class InMemoryToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolDefinition, ToolHandler]] = {}

    def register(self, tool: ToolDefinition, handler: ToolHandler) -> None:
        self._tools[tool.name] = (tool, handler)

    async def invoke(self, name: str, params: dict[str, object]) -> ToolResult:
        entry = self._tools.get(name)
        if entry is None:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' not registered",
            )

        _tool_def, handler = entry
        start = time.perf_counter()
        try:
            result = await handler(params)
            if not isinstance(result, ToolResult):
                result = ToolResult(success=True, data=result)
        except Exception as exc:
            result = ToolResult(success=False, error=str(exc))
        result.duration_ms = (time.perf_counter() - start) * 1000
        return result

    def list_tools(self) -> list[ToolDefinition]:
        return [tool_def for tool_def, _handler in self._tools.values()]
