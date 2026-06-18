from __future__ import annotations

from typing import Any

from pydantic_ai.agent import Agent
from pydantic_ai.settings import ModelSettings

from kosmo.contracts.llm.ports import LLMResponse, LLMUsage, PromptTemplate


class PydanticAILLMClient:
    def __init__(self, model: Any) -> None:
        self._model = model

    async def complete(
        self,
        prompt: PromptTemplate,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        agent = Agent(model=self._model, system_prompt=prompt.system_prompt)  # type: ignore[reportCallIssue]

        result = await agent.run(
            prompt.user_prompt,
            model_settings=ModelSettings(temperature=temperature, max_tokens=max_tokens),
        )
        text = result.output

        return LLMResponse(
            text=text,
            usage=LLMUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            ),
            model=getattr(result, "model_name", ""),
        )

    async def complete_json(
        self,
        prompt: PromptTemplate,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        return await self.complete(prompt=prompt, temperature=temperature, max_tokens=max_tokens)
