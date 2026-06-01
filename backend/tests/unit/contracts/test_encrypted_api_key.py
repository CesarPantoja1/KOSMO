from kosmo.contracts.llm.api_key import EncryptedApiKey, LLMProvider
from kosmo.contracts.sdd.ids import UserId


class TestEncryptedApiKey:
    def test_encrypted_api_key_creation(self) -> None:
        key = EncryptedApiKey(
            key_id="key-1",
            user_id=UserId("user-1"),
            provider=LLMProvider.ANTHROPIC,
            cipher_text="encrypted-data",
        )
        assert key.key_id == "key-1"
        assert key.provider == LLMProvider.ANTHROPIC

    def test_cipher_text_excluded_from_serialization(self) -> None:
        key = EncryptedApiKey(
            key_id="key-1",
            user_id=UserId("user-1"),
            provider=LLMProvider.OPENAI,
            cipher_text="secret",
        )
        data = key.model_dump()
        assert "cipher_text" not in data

    def test_llm_provider_values(self) -> None:
        assert LLMProvider.ANTHROPIC == "anthropic"
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.GOOGLE == "google"
        assert LLMProvider.NOOP == "noop"
