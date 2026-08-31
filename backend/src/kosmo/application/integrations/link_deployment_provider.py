from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime

from kosmo.contracts.auth.principal import Principal
from kosmo.contracts.auth.secrets import SecretCipher
from kosmo.contracts.integrations.deployment import (
    DeploymentAuthenticationError,
    DeploymentProvider,
    DeploymentProviderPort,
    UserDeploymentIntegration,
    UserDeploymentIntegrationRepository,
)
from kosmo.contracts.sdd.ids import UserId
from kosmo.contracts.telemetry import traced


@dataclass(frozen=True, slots=True)
class LinkDeploymentPlatformCommand:
    code: str
    provider: DeploymentProvider = DeploymentProvider.RAILWAY


LinkDeploymentProviderCommand = LinkDeploymentPlatformCommand


class LinkDeploymentPlatformUseCase:
    """Caso de uso para intercambiar el código OAuth de una plataforma de despliegue y persistir el token cifrado."""

    def __init__(
        self,
        deployment_client: DeploymentProviderPort,
        cipher: SecretCipher,
        repo: UserDeploymentIntegrationRepository,
    ) -> None:
        self._deployment_client = deployment_client
        self._cipher = cipher
        self._repo = repo

    @traced("deployment.link_platform")
    async def execute(
        self,
        principal: Principal,
        cmd: LinkDeploymentPlatformCommand,
    ) -> UserDeploymentIntegration:
        if not cmd.code or not cmd.code.strip():
            raise DeploymentAuthenticationError("El código de autorización OAuth no puede estar vacío.")

        token = await self._deployment_client.exchange_oauth_code(cmd.code.strip())
        if not token.access_token or not token.access_token.strip():
            raise DeploymentAuthenticationError("No se recibió un access_token válido de la plataforma de despliegue.")

        encrypted = self._cipher.encrypt(token.access_token.strip().encode("utf-8"))
        encrypted_token_str = base64.b64encode(encrypted.ciphertext).decode("utf-8")

        integration = UserDeploymentIntegration(
            user_id=UserId(principal.subject),
            provider=cmd.provider,
            encrypted_token=encrypted_token_str,
            provider_username=None,
            updated_at=datetime.now(UTC),
        )

        await self._repo.save(integration)
        return integration


LinkDeploymentProviderUseCase = LinkDeploymentPlatformUseCase
VincularPlataformaDespliegueUseCase = LinkDeploymentPlatformUseCase
