from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kosmo.contracts.ai.ai_config import AIProvider, UserAiConfig
from kosmo.contracts.auth.secrets import EncryptedSecret
from kosmo.contracts.llm.ports import LLMResponse, PromptTemplate
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
