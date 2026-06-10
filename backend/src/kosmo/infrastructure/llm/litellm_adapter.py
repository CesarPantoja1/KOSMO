from pydantic import BaseModel

from kosmo.contracts.llm.ports import LLMResponse, LLMUsage, PromptTemplate
from kosmo.infrastructure.security.key_vault import FernetApiKeyVault


class LiteLLMClient:
    def __init__(self, key_vault: FernetApiKeyVault) -> None:
        self._key_vault = key_vault
        self._default_model = "claude-sonnet-4-20250514"

    async def complete(
        self,
        prompt: PromptTemplate,
        response_schema: type[BaseModel] | None = None,
        temperature: float = 0,
        max_tokens: int | None = None,
        cache_key: str | None = None,
    ) -> LLMResponse:
        try:
            import litellm  # type: ignore[import-untyped]

            messages: list[dict[str, str]] = []
            if prompt.system_prompt:
                messages.append({"role": "system", "content": prompt.system_prompt})
            messages.append({"role": "user", "content": prompt.user_prompt})

            schema_to_parse: type[BaseModel] | None = response_schema or prompt.response_schema
            completion_kwargs: dict[str, object] = {
                "model": f"anthropic/{self._default_model}",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 4096,
            }
            if schema_to_parse is not None:
                completion_kwargs["response_format"] = schema_to_parse

            response = await litellm.acompletion(**completion_kwargs)

            content: str = response.choices[0].message.content or ""  # type: ignore[union-attr,assignment]
            usage = response.usage or litellm.Usage()  # type: ignore[union-attr]

            parsed: BaseModel | None = None
            if schema_to_parse is not None:
                try:
                    parsed = schema_to_parse.model_validate_json(content)
                except Exception:
                    pass

            return LLMResponse(
                content=content,
                usage=LLMUsage(
                    prompt_tokens=usage.prompt_tokens or 0,  # type: ignore[union-attr]
                    completion_tokens=usage.completion_tokens or 0,  # type: ignore[union-attr]
                    total_tokens=usage.total_tokens or 0,  # type: ignore[union-attr]
                ),
                model_id=self._default_model,
                parsed=parsed,
            )
        except ImportError:
            return LLMResponse(
                content="{}",
                usage=LLMUsage(),
                model_id="litellm-unavailable",
            )

    async def stream(  # noqa: ARG002
        self,
        prompt: PromptTemplate,
        temperature: float = 0,
        max_tokens: int | None = None,
    ) -> object:
        class _StubStream:
            async def __aiter__(self) -> "_StubStream":
                return self

            async def __anext__(self) -> str:
                raise StopAsyncIteration

        return _StubStream()
