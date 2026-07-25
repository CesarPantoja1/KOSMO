from __future__ import annotations

from typing import Any

from pydantic_ai.agent import Agent
from pydantic_ai.settings import ModelSettings

from kosmo.contracts.llm.ports import LLMResponse, LLMUsage, PromptTemplate


class PydanticAILLMClient:
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

        result = await agent.run(
            prompt.user_prompt,
            model_settings=ModelSettings(temperature=temperature, max_tokens=max_tokens),
        )

        usage = result.usage()
        return LLMResponse(
            text=result.output,
            usage=LLMUsage(
                prompt_tokens=usage.request_tokens,
                completion_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
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
