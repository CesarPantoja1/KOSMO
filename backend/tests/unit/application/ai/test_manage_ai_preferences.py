from unittest.mock import AsyncMock, MagicMock

import pytest

from kosmo.application.ai.manage_ai_preferences import ManageAIPreferencesUseCase
from kosmo.contracts.ai.ai_config import (
    DEFAULT_AI_MODEL,
    DEFAULT_AI_PROVIDER,
    AIProvider,
    SaveAIConfigInput,
    UserAiConfig,
)
from kosmo.contracts.auth.secrets import EncryptedSecret


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def mock_cipher():
    cipher = MagicMock()
    cipher.encrypt.side_effect = lambda data: EncryptedSecret(ciphertext=b"encrypted_" + data)
    cipher.decrypt.side_effect = lambda secret: secret.ciphertext.replace(b"encrypted_", b"")
    return cipher


@pytest.fixture
def use_case(mock_repo, mock_cipher):
    return ManageAIPreferencesUseCase(config_repo=mock_repo, cipher=mock_cipher)


@pytest.mark.asyncio
async def test_get_preferences_returns_default_when_not_found(use_case, mock_repo):
    mock_repo.by_user_id.return_value = None
    result = await use_case.get_preferences("user-1")
    assert result.provider == DEFAULT_AI_PROVIDER
    assert result.model == DEFAULT_AI_MODEL
    assert result.is_custom is False
    assert result.has_api_key is False
    assert result.masked_key is None


@pytest.mark.asyncio
async def test_get_preferences_returns_masked_key(use_case, mock_repo):
    mock_repo.by_user_id.return_value = UserAiConfig(
        user_id="user-1",
        provider=AIProvider.OPENAI,
        model="gpt-4",
        encrypted_api_key=EncryptedSecret(ciphertext=b"encrypted_sk-1234567890"),
        is_custom=False,
    )
    result = await use_case.get_preferences("user-1")
    assert result.provider == AIProvider.OPENAI
    assert result.model == "gpt-4"
    assert result.has_api_key is True
    assert result.masked_key == "••••••••7890"


@pytest.mark.asyncio
async def test_save_preferences_encrypts_and_saves(use_case, mock_repo):
    input_data = SaveAIConfigInput(
        provider=AIProvider.ANTHROPIC,
        model="claude-3-opus-20240229",
        api_key="sk-ant-123456789",
    )

    mock_repo.save.return_value = UserAiConfig(
        user_id="user-1",
        provider=input_data.provider,
        model=input_data.model,
        encrypted_api_key=EncryptedSecret(ciphertext=b"encrypted_sk-ant-123456789"),
    )

    result = await use_case.save_preferences("user-1", input_data)

    mock_repo.save.assert_called_once()
    assert result.masked_key == "••••••••6789"


@pytest.mark.asyncio
async def test_delete_preferences(use_case, mock_repo):
    await use_case.delete_preferences("user-1")
    mock_repo.delete.assert_called_once_with("user-1")


@pytest.mark.asyncio
async def test_get_generation_credentials(use_case, mock_repo):
    mock_repo.by_user_id.return_value = UserAiConfig(
        user_id="user-1",
        provider=AIProvider.GOOGLE,
        model="gemini-1.5-pro",
        encrypted_api_key=EncryptedSecret(ciphertext=b"encrypted_AIzaSyFakeKey123"),
    )
    provider, model, api_key = await use_case.get_generation_credentials("user-1")
    assert provider == AIProvider.GOOGLE
    assert model == "gemini-1.5-pro"
    assert api_key == "AIzaSyFakeKey123"


@pytest.mark.asyncio
async def test_get_generation_credentials_returns_default(use_case, mock_repo):
    mock_repo.by_user_id.return_value = None
    provider, model, api_key = await use_case.get_generation_credentials("user-1")
    assert provider == DEFAULT_AI_PROVIDER
    assert model == DEFAULT_AI_MODEL
    assert api_key is None
