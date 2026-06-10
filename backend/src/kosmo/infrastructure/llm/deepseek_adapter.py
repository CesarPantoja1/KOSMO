import httpx
from pydantic import BaseModel

from kosmo.contracts.llm.ports import LLMResponse, LLMUsage, PromptTemplate

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_CHAT_MODEL = "deepseek-chat"


class DeepSeekClient:
    def __init__(self, api_key: str, model: str = DEEPSEEK_CHAT_MODEL) -> None:
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=DEEPSEEK_BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    async def complete(
        self,
        prompt: PromptTemplate,
        response_schema: type[BaseModel] | None = None,
        temperature: float = 0,
        max_tokens: int | None = None,
        cache_key: str | None = None,
    ) -> LLMResponse:
        import structlog

        log = structlog.get_logger()

        messages: list[dict[str, str]] = []
        if prompt.system_prompt:
            messages.append({"role": "system", "content": prompt.system_prompt})
        messages.append({"role": "user", "content": prompt.user_prompt})

        body: dict[str, object] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            "stream": False,
        }

        schema_to_parse: type[BaseModel] | None = response_schema or prompt.response_schema
        if schema_to_parse is not None:
            body["response_format"] = {"type": "json_object"}

        log.debug("deepseek.request", model=self._model, msg_count=len(messages))

        response = await self._client.post("/v1/chat/completions", json=body)

        if response.status_code != 200:
            error_body = response.text
            log.error(
                "deepseek.api_error",
                status=response.status_code,
                body=error_body[:500],
            )
            raise Exception(f"DeepSeek API error {response.status_code}: {error_body[:300]}")

        data = response.json()
        choice = data["choices"][0]
        content: str = choice["message"]["content"]  # type: ignore[assignment]
        usage_raw = data.get("usage", {})

        log.debug(
            "deepseek.response",
            model=self._model,
            tokens=usage_raw.get("total_tokens", 0),
            content_len=len(content),
        )

        parsed: BaseModel | None = None
        if schema_to_parse is not None:
            try:
                parsed = schema_to_parse.model_validate_json(content)
            except Exception:
                pass

        return LLMResponse(
            content=content,
            usage=LLMUsage(
                prompt_tokens=usage_raw.get("prompt_tokens", 0),
                completion_tokens=usage_raw.get("completion_tokens", 0),
                total_tokens=usage_raw.get("total_tokens", 0),
            ),
            model_id=self._model,
            parsed=parsed,
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

    async def close(self) -> None:
        await self._client.aclose()
