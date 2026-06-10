from __future__ import annotations

import pytest

from kosmo.contracts.orchestration.tools import (
    ToolDefinition,
    ToolInputSchema,
    ToolOutputSchema,
    ToolResult,
)
from kosmo.domain.agents.tool_registry import InMemoryToolRegistry


async def _echo_handler(params: dict[str, object]) -> ToolResult:
    return ToolResult(success=True, data=params)


async def _failing_handler(params: dict[str, object]) -> ToolResult:
    raise ValueError("Handler failed")


@pytest.mark.unit
class TestInMemoryToolRegistry:
    async def test_register_and_list(self) -> None:
        registry = InMemoryToolRegistry()
        tool = ToolDefinition(name="echo", description="Echo tool")
        registry.register(tool, _echo_handler)

        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "echo"

    async def test_invoke_returns_result(self) -> None:
        registry = InMemoryToolRegistry()
        tool = ToolDefinition(name="echo", description="Echo tool")
        registry.register(tool, _echo_handler)

        result = await registry.invoke("echo", {"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.duration_ms is not None

    async def test_invoke_unregistered_tool_errors(self) -> None:
        registry = InMemoryToolRegistry()
        result = await registry.invoke("nonexistent", {})
        assert result.success is False
        assert "not registered" in (result.error or "")

    async def test_register_duplicate_overwrites(self) -> None:
        registry = InMemoryToolRegistry()
        t1 = ToolDefinition(name="tool", description="First")
        t2 = ToolDefinition(name="tool", description="Second")
        registry.register(t1, _echo_handler)
        registry.register(t2, _echo_handler)

        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0].description == "Second"

    async def test_invoke_handles_handler_exception(self) -> None:
        registry = InMemoryToolRegistry()
        tool = ToolDefinition(name="fail")
        registry.register(tool, _failing_handler)

        result = await registry.invoke("fail", {})
        assert result.success is False
        assert "Handler failed" in (result.error or "")
        assert result.duration_ms is not None

    async def test_list_tools_empty_registry(self) -> None:
        registry = InMemoryToolRegistry()
        assert registry.list_tools() == []


@pytest.mark.unit
class TestToolDefinition:
    def test_default_schemas_are_empty(self) -> None:
        tool = ToolDefinition(name="test")
        assert tool.input_schema.parameters == {}
        assert tool.output_schema.result_schema == {}

    def test_custom_schemas(self) -> None:
        tool = ToolDefinition(
            name="test",
            description="A test tool",
            input_schema=ToolInputSchema(parameters={"type": "object"}),
            output_schema=ToolOutputSchema(result_schema={"type": "string"}),
        )
        assert tool.input_schema.parameters == {"type": "object"}
        assert tool.output_schema.result_schema == {"type": "string"}


@pytest.mark.unit
class TestToolResult:
    def test_default_values(self) -> None:
        result = ToolResult(success=True)
        assert result.success is True
        assert result.data is None
        assert result.error is None

    def test_error_result(self) -> None:
        result = ToolResult(success=False, error="Something broke")
        assert result.success is False
        assert result.error == "Something broke"
