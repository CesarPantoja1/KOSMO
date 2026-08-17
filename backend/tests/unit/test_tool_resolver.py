from __future__ import annotations

from typing import Any

import pytest

from kosmo.application.pipeline.tool_resolver import ToolResolver
from kosmo.contracts.llm.ports import LLMResponse, LLMUsage, PromptTemplate
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.pipeline.knowledge_tool_registry import KnowledgeToolDef, KnowledgeToolRegistry


class _StubCompleteText:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._index = 0

    async def complete(self, prompt: PromptTemplate, temperature: float = 0.3, max_tokens: int = 4096) -> LLMResponse:
        text = self._responses[min(self._index, len(self._responses) - 1)]
        self._index += 1
        return LLMResponse(text=text, usage=LLMUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2))

    @property
    def supports_native_tools(self) -> bool:
        return False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_without_knowledge_tools_returns_not_available_reason() -> None:
    # Arrange
    resolver = ToolResolver(llm_client=_StubCompleteText(["[CONTINUE]"]), knowledge_tools=None)

    # Act
    context, invocations, reasons = await resolver.resolve("sys", "user", ProjectId("prj_01"))

    # Assert
    assert context == ""
    assert invocations == []
    assert reasons == ["pre_consulta_tools: no disponible"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_with_empty_registry_returns_no_tools_reason() -> None:
    # Arrange
    resolver = ToolResolver(llm_client=_StubCompleteText(["[CONTINUE]"]), knowledge_tools=KnowledgeToolRegistry())

    # Act
    context, invocations, reasons = await resolver.resolve("sys", "user", None)

    # Assert
    assert context == ""
    assert invocations == []
    assert reasons == ["pre_consulta_tools: sin herramientas registradas"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_knowledge_tools_text_fallback_continues_without_tools() -> None:
    # Arrange
    resolver = ToolResolver(llm_client=_StubCompleteText(["[CONTINUE]"]), knowledge_tools=KnowledgeToolRegistry())

    # Act
    context, invocations = await resolver.resolve_knowledge_tools("sys", "user", None)

    # Assert
    assert context == ""
    assert invocations == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_knowledge_tools_executes_tool_and_collects_result() -> None:
    # Arrange
    registry = KnowledgeToolRegistry()

    async def _handler(tool_input: dict[str, Any]) -> str:
        return f"documento de {tool_input.get('project_id')}"

    registry.register(
        KnowledgeToolDef(
            name="get_phase_document", description="Devuelve el documento", parameters={"project_id": "str"}
        ),
        _handler,
    )
    resolver = ToolResolver(
        llm_client=_StubCompleteText(['[TOOL: get_phase_document] {"project_id": "prj_01"}', "[CONTINUE]"]),
        knowledge_tools=registry,
    )

    # Act
    context, invocations = await resolver.resolve_knowledge_tools("sys", "user", ProjectId("prj_01"))

    # Assert
    assert "documento de prj_01" in context
    assert len(invocations) == 1
    assert invocations[0]["tool"] == "get_phase_document"
    assert invocations[0]["found"] is True
