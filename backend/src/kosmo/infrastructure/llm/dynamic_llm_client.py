from __future__ import annotations

import contextvars
from collections.abc import AsyncIterator
from typing import Any

import structlog

from kosmo.contracts.ai.ai_config import UserAiConfigRepository
from kosmo.contracts.auth import SecretCipher
from kosmo.contracts.auth.secrets import EncryptedSecret
from kosmo.contracts.llm.ports import LLMClient, LLMResponse, PromptTemplate, ToolCallRecord
from kosmo.contracts.sdd.errors import AIProviderAuthError
from kosmo.infrastructure.llm.noop_adapter import NoopLLMClient
from kosmo.infrastructure.llm.pydantic_ai_adapter import PydanticAILLMClient, StreamedTypedResult

current_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_user_id", default=None)

_log = structlog.get_logger(__name__)

_AUTH_ERROR_KEYWORDS = (
    "unauthorized",
    "authentication",
    "invalid_api_key",
    "api_key_invalid",
    "invalid api key",
    "incorrect api key",
    "permission_denied",
    "permissiondenied",
    "quota",
    "insufficient_quota",
    "credit",
    "401",
    "403",
)


def is_ai_auth_error(exc: Exception) -> bool:
    if isinstance(exc, AIProviderAuthError):
        return True
    err_str = str(exc).lower()
    type_str = type(exc).__name__.lower()
    return any(keyword in err_str or keyword in type_str for keyword in _AUTH_ERROR_KEYWORDS)


def build_pydantic_ai_model(provider: str, model: str, api_key: str | None) -> object:
    prov = provider.lower()
    if prov == "deepseek":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
        from pydantic_ai.settings import ModelSettings

        return OpenAIChatModel(
            model,
            provider=OpenAIProvider(base_url="https://api.deepseek.com", api_key=api_key),
            settings=ModelSettings(extra_body={"thinking": {"type": "disabled"}}),
        )
    if prov == "openai":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        return OpenAIChatModel(
            model,
            provider=OpenAIProvider(api_key=api_key),
        )
    if prov == "anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        return AnthropicModel(
            model,
            provider=AnthropicProvider(api_key=api_key),
        )
    if prov in ("google", "gemini"):
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        return GoogleModel(
            model,
            provider=GoogleProvider(api_key=api_key),
        )

    return f"{provider}:{model}"


class DynamicUserLLMClient(LLMClient):
    def __init__(
        self,
        config_repo: UserAiConfigRepository,
        cipher: SecretCipher,
        default_provider: str,
        default_model: str,
        default_api_key: str | None = None,
    ) -> None:
        self._config_repo = config_repo
        self._cipher = cipher
        self._default_provider = default_provider
        self._default_model = default_model
        self._default_api_key = default_api_key
        self._clients: dict[tuple[str, str, str | None], PydanticAILLMClient] = {}

    async def _resolve_client(self) -> LLMClient:
        user_id = current_user_id.get()
        provider = self._default_provider
        model = self._default_model
        api_key = self._default_api_key

        if user_id:
            try:
                user_config = await self._config_repo.by_user_id(user_id)
                if user_config and user_config.encrypted_api_key is not None:
                    secret = (
                        user_config.encrypted_api_key
                        if isinstance(user_config.encrypted_api_key, EncryptedSecret)
                        else EncryptedSecret(ciphertext=user_config.encrypted_api_key)
                    )
                    raw_key = self._cipher.decrypt(secret)
                    provider_str = (
                        user_config.provider.value
                        if hasattr(user_config.provider, "value")
                        else str(user_config.provider)
                    )
                    provider = provider_str
                    model = user_config.model
                    api_key = raw_key.decode("utf-8")
            except Exception:
                _log.warning("dynamic_llm_client.resolve_user_config_failed", user_id=user_id, exc_info=True)

        if provider.lower() == "noop":
            return NoopLLMClient()

        key_tuple = (provider, model, api_key)
        client = self._clients.get(key_tuple)
        if client is None:
            pydantic_model = build_pydantic_ai_model(provider, model, api_key)
            client = PydanticAILLMClient(model=pydantic_model)
            self._clients[key_tuple] = client
        return client

    async def complete(
        self,
        prompt: PromptTemplate,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        client = await self._resolve_client()
        try:
            return await client.complete(prompt=prompt, temperature=temperature, max_tokens=max_tokens)
        except Exception as exc:
            if is_ai_auth_error(exc):
                raise AIProviderAuthError() from exc
            raise

    async def complete_json(
        self,
        prompt: PromptTemplate,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        client = await self._resolve_client()
        try:
            return await client.complete_json(prompt=prompt, temperature=temperature, max_tokens=max_tokens)
        except Exception as exc:
            if is_ai_auth_error(exc):
                raise AIProviderAuthError() from exc
            raise

    async def complete_typed[T](
        self,
        prompt: PromptTemplate,
        output_type: type[T],
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> T:
        client = await self._resolve_client()
        try:
            return await client.complete_typed(
                prompt=prompt,
                output_type=output_type,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            if is_ai_auth_error(exc):
                raise AIProviderAuthError() from exc
            raise

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
        client = await self._resolve_client()
        if isinstance(client, PydanticAILLMClient):
            try:
                return await client.complete_with_tools(
                    prompt=prompt,
                    tools=tools,
                    tool_handler=tool_handler,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                if is_ai_auth_error(exc):
                    raise AIProviderAuthError() from exc
                raise
        return ("", [])

    def stream_typed[T](
        self,
        prompt: PromptTemplate,
        output_type: type[T],
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamedTypedResult[T]]:
        raise NotImplementedError("Streaming must resolve client dynamically via async context")
