from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class PromptTemplate(BaseModel):
    system_prompt: str = ""
    user_prompt: str
    few_shot_examples: list[dict[str, str]] | None = None
    cache_key: str | None = None


class LLMUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class LLMResponse(BaseModel):
    content: str
    usage: LLMUsage = LLMUsage()
    model_id: str = ""


@runtime_checkable
class LLMClient(Protocol):
    async def complete(
        self,
        prompt: PromptTemplate,
        response_schema: type | None = None,
        temperature: float = 0,
        max_tokens: int | None = None,
        cache_key: str | None = None,
    ) -> LLMResponse: ...

    async def stream(
        self,
        prompt: PromptTemplate,
        temperature: float = 0,
        max_tokens: int | None = None,
    ) -> object: ...
