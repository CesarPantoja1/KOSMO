from __future__ import annotations

from kosmo.contracts.ai.ai_config import (
    AIConnectionTester,
    AIProvider,
    InvalidApiKeyError,
    TestAIConnectionInput,
    TestAIConnectionResult,
    UserAiConfigRepository,
)
from kosmo.contracts.auth.secrets import EncryptedSecret, SecretCipher
from kosmo.contracts.telemetry import traced


class ValidateAIConnectionUseCase:
    """Caso de uso para comprobar la conectividad y validez de credenciales con proveedores de IA."""

    def __init__(
        self,
        connection_tester: AIConnectionTester,
        config_repo: UserAiConfigRepository | None = None,
        cipher: SecretCipher | None = None,
    ) -> None:
        self._tester = connection_tester
        self._config_repo = config_repo
        self._cipher = cipher

    @traced("ai_config.validate_connection")
    async def execute(self, input_data: TestAIConnectionInput) -> TestAIConnectionResult:
        api_key = await self._resolve_api_key(input_data)

        return await self._tester.test_connection(
            provider=input_data.provider,
            model=input_data.model.strip(),
            api_key=api_key,
        )

    async def _resolve_api_key(self, input_data: TestAIConnectionInput) -> str | None:
        if input_data.api_key is not None and input_data.api_key.strip():
            return input_data.api_key.strip()

        if input_data.provider == AIProvider.KOSMO_DEFAULT:
            return None

        if input_data.user_id is not None:
            if self._config_repo is None or self._cipher is None:
                raise InvalidApiKeyError("La clave de API es requerida para probar la conexión.")

            persisted = await self._config_repo.by_user_id(input_data.user_id)
            if persisted is None or not persisted.has_api_key or persisted.encrypted_api_key is None:
                raise InvalidApiKeyError(
                    "No se proporcionó una clave de API ni existe una clave guardada para este usuario."
                )

            if isinstance(persisted.encrypted_api_key, EncryptedSecret):
                return self._cipher.decrypt(persisted.encrypted_api_key).decode("utf-8")
            return self._cipher.decrypt(EncryptedSecret(ciphertext=persisted.encrypted_api_key)).decode("utf-8")

        raise InvalidApiKeyError("La clave de API es requerida para probar la conexión.")
