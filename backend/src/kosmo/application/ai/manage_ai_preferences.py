from __future__ import annotations

from kosmo.contracts.ai.ai_config import (
    DEFAULT_AI_MODEL,
    DEFAULT_AI_PROVIDER,
    AIConfigView,
    AIProvider,
    SaveAIConfigInput,
    UserAiConfig,
    UserAiConfigRepository,
    mask_api_key,
)
from kosmo.contracts.auth.secrets import EncryptedSecret, SecretCipher
from kosmo.contracts.telemetry import traced


class ManageAIPreferencesUseCase:
    """Caso de uso para la gestión de preferencias de IA de los usuarios."""

    def __init__(self, config_repo: UserAiConfigRepository, cipher: SecretCipher) -> None:
        self._repo = config_repo
        self._cipher = cipher

    @traced("ai_config.get_preferences")
    async def get_preferences(self, user_id: str) -> AIConfigView:
        """Consulta las preferencias del usuario y retorna la vista con la llave enmascarada."""
        config = await self._repo.by_user_id(user_id)
        if config is None:
            return AIConfigView(
                provider=DEFAULT_AI_PROVIDER,
                model=DEFAULT_AI_MODEL,
                is_custom=False,
                has_api_key=False,
                masked_key=None,
            )

        masked_key = None
        if config.has_api_key and config.encrypted_api_key is not None:
            if isinstance(config.encrypted_api_key, EncryptedSecret):
                decrypted = self._cipher.decrypt(config.encrypted_api_key).decode("utf-8")
            else:
                decrypted = self._cipher.decrypt(EncryptedSecret(ciphertext=config.encrypted_api_key)).decode("utf-8")
            masked_key = mask_api_key(decrypted)

        return config.to_view(masked_key=masked_key)

    @traced("ai_config.save_preferences")
    async def save_preferences(self, user_id: str, data: SaveAIConfigInput) -> AIConfigView:
        """Guarda o actualiza las preferencias del usuario."""
        encrypted_key = self._cipher.encrypt(data.api_key.encode("utf-8"))

        is_custom = data.provider != AIProvider.KOSMO_DEFAULT

        config = UserAiConfig(
            user_id=user_id,
            provider=data.provider,
            model=data.model.strip(),
            encrypted_api_key=encrypted_key,
            is_custom=is_custom,
        )
        saved_config = await self._repo.save(config)

        # Para la respuesta devolvemos la misma llave enmascarada (ya validada)
        return saved_config.to_view(masked_key=mask_api_key(data.api_key))

    @traced("ai_config.delete_preferences")
    async def delete_preferences(self, user_id: str) -> None:
        """Elimina la configuración de IA del usuario."""
        await self._repo.delete(user_id)

    @traced("ai_config.get_generation_credentials")
    async def get_generation_credentials(self, user_id: str) -> tuple[AIProvider, str, str | None]:
        """Obtiene credenciales descifradas para el uso interno del motor de IA."""
        config = await self._repo.by_user_id(user_id)
        if config is None:
            return (DEFAULT_AI_PROVIDER, DEFAULT_AI_MODEL, None)

        api_key = None
        if config.has_api_key and config.encrypted_api_key is not None:
            if isinstance(config.encrypted_api_key, EncryptedSecret):
                api_key = self._cipher.decrypt(config.encrypted_api_key).decode("utf-8")
            else:
                api_key = self._cipher.decrypt(EncryptedSecret(ciphertext=config.encrypted_api_key)).decode("utf-8")

        return (config.provider, config.model, api_key)
