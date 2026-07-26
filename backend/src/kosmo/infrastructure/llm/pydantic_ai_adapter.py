from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel
from pydantic_ai.agent import Agent
from pydantic_ai.settings import ModelSettings
from pydantic_ai.tools import Tool

from kosmo.contracts.llm.ports import LLMResponse, LLMUsage, PromptTemplate, ToolCallRecord


def _extract_json(text: str) -> str | None:
    """Extrae el primer objeto o array JSON del texto, tolerando markdown y texto circundante."""
    # Quitar fences markdown (```json ... ``` o ``` ... ```)
    if "```json" in text:
        text = text.split("```json", 1)[1]
        if "```" in text:
            text = text.split("```", 1)[0]
    elif text.count("```") >= 2:
        parts = text.split("```")
        text = parts[1]

    # Buscar el primer { o [
    for start_char in ("{", "["):
        idx = text.find(start_char)
        if idx != -1:
            return _extract_balanced(text, idx, start_char)

    return None


def _extract_balanced(text: str, start: int, open_char: str) -> str | None:
    close_char = "}" if open_char == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


class PydanticAILLMClient:
    _DEFAULT_TIMEOUT_SECONDS = 120

    def __init__(self, model: Any) -> None:
        self._model = model
        self._agents: dict[str, Agent[Any]] = {}

    def _get_agent(self, system_prompt: str) -> Agent[Any]:
        agent = self._agents.get(system_prompt)
        if agent is None:
            agent = Agent(model=self._model, system_prompt=system_prompt)  # type: ignore[reportCallIssue]
            self._agents[system_prompt] = agent
        return agent

    async def complete(
        self,
        prompt: PromptTemplate,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        agent = self._get_agent(prompt.system_prompt)

        result = await asyncio.wait_for(
            agent.run(
                prompt.user_prompt,
                model_settings=ModelSettings(temperature=temperature, max_tokens=max_tokens),
            ),
            timeout=self._DEFAULT_TIMEOUT_SECONDS,
        )

        usage = result.usage()
        return LLMResponse(
            text=result.output,
            usage=LLMUsage(
                prompt_tokens=usage.input_tokens,
                completion_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
            ),
            model=getattr(result, "model_name", ""),
        )

    async def complete_typed[T](
        self,
        prompt: PromptTemplate,
        output_type: type[T],
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> T:
        response = await self.complete(prompt=prompt, temperature=temperature, max_tokens=max_tokens)
        text = response.text.strip()

        # Intentar extraer JSON incluso si hay texto circundante o markdown
        json_text = _extract_json(text)
        if json_text:
            try:
                return output_type.model_validate_json(json_text)  # type: ignore[reportReturnType]
            except Exception:
                pass

        # Si el texto completo es JSON valido
        if text.startswith("{") or text.startswith("["):
            try:
                return output_type.model_validate_json(text)  # type: ignore[reportReturnType]
            except Exception:
                pass

        # Fallback para modelos de un solo campo (DiscoveryDocument, RequirementsDocument, DiagramSpec)
        if issubclass(output_type, BaseModel):
            field_names = list(output_type.model_fields.keys())
            if len(field_names) == 1:
                return output_type.model_validate({field_names[0]: text})  # type: ignore[reportReturnType]

        msg = f"No se pudo convertir la respuesta del LLM a {output_type.__name__}"
        raise ValueError(msg)

    async def complete_json(
        self,
        prompt: PromptTemplate,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        return await self.complete(prompt=prompt, temperature=temperature, max_tokens=max_tokens)

    @property
    def supports_native_tools(self) -> bool:
        return True

    async def complete_with_tools(
        self,
        prompt: PromptTemplate,
        tools: list[dict[str, Any]],
        tool_handler: Any,
        temperature: float = 0.1,
        max_tokens: int = 2000,
    ) -> tuple[str, list[ToolCallRecord]]:
        records: list[ToolCallRecord] = []

        def _make_tool_fn(name: str):
            async def tool_fn(**kwargs: object) -> str:
                args: dict[str, Any] = dict(kwargs)
                result = await tool_handler(name, args)
                records.append(
                    ToolCallRecord(name=name, args=args, result_snippet=(result or "")[:500])
                )
                return result
            tool_fn.__name__ = name  # type: ignore[reportFunctionMemberAccess]
            return tool_fn

        pydantic_tools = [
            Tool(
                _make_tool_fn(t["name"]),
                name=t["name"],
                description=t.get("description", ""),
            )
            for t in tools
        ]

        agent: Agent[Any] = Agent(self._model, system_prompt=prompt.system_prompt, tools=pydantic_tools)  # type: ignore[reportCallIssue]
        result = await asyncio.wait_for(
            agent.run(
                prompt.user_prompt,
                model_settings=ModelSettings(temperature=temperature, max_tokens=max_tokens),
            ),
            timeout=self._DEFAULT_TIMEOUT_SECONDS,
        )

        return (result.output or "", records)
