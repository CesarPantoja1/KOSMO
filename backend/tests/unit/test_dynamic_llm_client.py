from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kosmo.contracts.ai.ai_config import AIProvider, UserAiConfig
from kosmo.contracts.auth.secrets import EncryptedSecret
from kosmo.contracts.llm.ports import LLMResponse, PromptTemplate
from kosmo.contracts.sdd.errors import AIProviderAuthError
from kosmo.infrastructure.llm.dynamic_llm_client import DynamicUserLLMClient, current_user_id


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def mock_cipher():
    cipher = MagicMock()
    cipher.decrypt.side_effect = lambda secret: secret.ciphertext.replace(b"enc_", b"")
    return cipher


@pytest.fixture
def dynamic_client(mock_repo, mock_cipher):
    return DynamicUserLLMClient(
        config_repo=mock_repo,
        cipher=mock_cipher,
        default_provider="openai",
        default_model="gpt-4o",
        default_api_key="sk-default-key",
    )


@pytest.mark.asyncio
async def test_dynamic_client_resolves_user_credentials(dynamic_client, mock_repo):
    # Arrange
    user_id = "usr_test_123"
    current_user_id.set(user_id)

    mock_repo.by_user_id.return_value = UserAiConfig(
        user_id=user_id,
        provider=AIProvider.DEEPSEEK,
        model="deepseek-v4-flash",
        encrypted_api_key=EncryptedSecret(ciphertext=b"enc_sk-user-deepseek-key"),
        is_custom=True,
    )

    mock_pydantic_client = AsyncMock()
    mock_pydantic_client.complete.return_value = LLMResponse(text="response from user deepseek")

    with patch("kosmo.infrastructure.llm.dynamic_llm_client.PydanticAILLMClient", return_value=mock_pydantic_client):
        # Act
        prompt = PromptTemplate(system_prompt="sys", user_prompt="hello")
        res = await dynamic_client.complete(prompt)

        # Assert
        assert res.text == "response from user deepseek"
        mock_repo.by_user_id.assert_called_once_with(user_id)


@pytest.mark.asyncio
async def test_dynamic_client_falls_back_when_no_user_config(dynamic_client, mock_repo):
    # Arrange
    current_user_id.set(None)
    mock_repo.by_user_id.return_value = None

    mock_pydantic_client = AsyncMock()
    mock_pydantic_client.complete.return_value = LLMResponse(text="response from default")

    with patch("kosmo.infrastructure.llm.dynamic_llm_client.PydanticAILLMClient", return_value=mock_pydantic_client):
        # Act
        prompt = PromptTemplate(system_prompt="sys", user_prompt="hello")
        res = await dynamic_client.complete(prompt)

        # Assert
        assert res.text == "response from default"
        mock_repo.by_user_id.assert_not_called()


@pytest.mark.asyncio
async def test_dynamic_client_stream_typed_delegates_to_resolved_client(dynamic_client, mock_repo):
    # Arrange
    user_id = "usr_test_stream"
    current_user_id.set(user_id)

    mock_repo.by_user_id.return_value = None

    class FakeStreamedResult:
        async def stream_text(self, *, delta: bool = False):  # noqa: ARG002
            yield "chunk 1"
            yield "chunk 2"

        async def get_data(self):
            return "final result"

    @asynccontextmanager
    async def fake_stream_typed(*_args, **_kwargs):
        yield FakeStreamedResult()

    mock_pydantic_client = AsyncMock()
    mock_pydantic_client.stream_typed = fake_stream_typed

    with patch("kosmo.infrastructure.llm.dynamic_llm_client.PydanticAILLMClient", return_value=mock_pydantic_client):
        # Act
        prompt = PromptTemplate(system_prompt="sys", user_prompt="hello")
        chunks = []
        async with dynamic_client.stream_typed(prompt=prompt, output_type=str) as streamed:
            async for chunk in streamed.stream_text(delta=True):
                chunks.append(chunk)
            result = await streamed.get_data()

        # Assert
        assert chunks == ["chunk 1", "chunk 2"]
        assert result == "final result"


@pytest.mark.asyncio
async def test_dynamic_client_stream_typed_maps_auth_error(dynamic_client, mock_repo):
    # Arrange
    current_user_id.set(None)
    mock_repo.by_user_id.return_value = None

    @asynccontextmanager
    async def fake_stream_typed_error(*_args, **_kwargs):
        raise ValueError("401 unauthorized invalid_api_key")
        yield  # type: ignore[unreachable]

    mock_pydantic_client = AsyncMock()
    mock_pydantic_client.stream_typed = fake_stream_typed_error

    with patch("kosmo.infrastructure.llm.dynamic_llm_client.PydanticAILLMClient", return_value=mock_pydantic_client):
        prompt = PromptTemplate(system_prompt="sys", user_prompt="hello")
        with pytest.raises(AIProviderAuthError):
            async with dynamic_client.stream_typed(prompt=prompt, output_type=str):
                pass


@pytest.mark.asyncio
async def test_dynamic_client_stream_typed_with_noop(mock_repo, mock_cipher):
    # Arrange
    client = DynamicUserLLMClient(
        config_repo=mock_repo,
        cipher=mock_cipher,
        default_provider="noop",
        default_model="noop",
    )
    current_user_id.set(None)

    prompt = PromptTemplate(system_prompt="sys", user_prompt="hello")
    chunks = []
    async with client.stream_typed(prompt=prompt, output_type=str) as streamed:
        async for chunk in streamed.stream_text(delta=True):
            chunks.append(chunk)
        result = await streamed.get_data()

    assert len(chunks) > 0
    assert result is not None
