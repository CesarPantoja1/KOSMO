from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class PromptTemplate:
    system_prompt: str
    user_prompt: str


@dataclass(frozen=True)
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class LLMResponse:
    text: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    model: str = ""
    finish_reason: str = ""


class LLMClient(Protocol):
    async def complete(
        self,
        prompt: PromptTemplate,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse: ...

    async def complete_json(
        self,
        prompt: PromptTemplate,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse: ...

    async def complete_typed[T](
        self,
        prompt: PromptTemplate,
        output_type: type[T],
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> T: ...


class Embedder(Protocol):
    @property
    def model_name(self) -> str: ...

    async def embed(self, text: str) -> list[float] | None: ...

    @staticmethod
    def text_for_embedding(output: object, validation_errors: list[str]) -> str:
        parts = [str(output)[:2000]]
        if validation_errors:
            parts.append("Errores: " + "; ".join(validation_errors[:5]))
        return "\n".join(parts)
