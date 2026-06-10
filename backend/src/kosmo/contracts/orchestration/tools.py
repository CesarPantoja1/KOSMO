from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ToolInputSchema(BaseModel):
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for tool input parameters"
    )


class ToolOutputSchema(BaseModel):
    result_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for tool output"
    )


class ToolDefinition(BaseModel):
    name: str
    description: str = ""
    input_schema: ToolInputSchema = Field(default_factory=ToolInputSchema)
    output_schema: ToolOutputSchema = Field(default_factory=ToolOutputSchema)

    model_config = {"arbitrary_types_allowed": True}


class ToolResult(BaseModel):
    success: bool
    data: object | None = None
    error: str | None = None
    duration_ms: float | None = None


ToolHandler = Callable[..., Awaitable[ToolResult]]


@runtime_checkable
class ToolRegistry(Protocol):
    def register(self, tool: ToolDefinition, handler: ToolHandler) -> None: ...

    async def invoke(self, name: str, params: dict[str, object]) -> ToolResult: ...

    def list_tools(self) -> list[ToolDefinition]: ...
