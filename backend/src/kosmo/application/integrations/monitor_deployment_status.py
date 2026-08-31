import asyncio
import base64
from dataclasses import dataclass, replace

from kosmo.contracts.auth.secrets import EncryptedSecret, SecretCipher
from kosmo.contracts.integrations.deployment import (
    DeploymentAuthenticationError,
    DeploymentProviderPort,
    DeploymentStatus,
    ProjectDeploymentRepository,
    UserDeploymentIntegrationRepository,
)
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.telemetry import traced


@dataclass(frozen=True, slots=True)
class MonitorDeploymentStatusCommand:
    project_id: ProjectId
    user_id: UserId
    max_attempts: int = 60
    delay_seconds: int = 10


class MonitorDeploymentStatusUseCase:
    """Caso de uso para monitorear periÃ³dicamente el estado de un despliegue en la nube."""

    def __init__(
        self,
        project_deployment_repo: ProjectDeploymentRepository,
        user_deployment_repo: UserDeploymentIntegrationRepository,
        deployment_client: DeploymentProviderPort,
        cipher: SecretCipher,
    ) -> None:
        self._project_deployment_repo = project_deployment_repo
        self._user_deployment_repo = user_deployment_repo
        self._deployment_client = deployment_client
        self._cipher = cipher

    @traced("deployment.monitor")
    async def execute(self, cmd: MonitorDeploymentStatusCommand) -> None:
        # 1. Recuperar el ProjectDeployment
        deployment = await self._project_deployment_repo.get_by_project_id(cmd.project_id)
        if not deployment or not deployment.service_id:
            return  # No hay nada que monitorear

        # Si ya alcanzÃ³ un estado terminal, terminar de inmediato
        if deployment.status in (DeploymentStatus.PUBLISHED, DeploymentStatus.FAILED):
            return

        # 2. Obtener el token de despliegue del usuario
        user_integration = await self._user_deployment_repo.get_by_user_id(cmd.user_id, deployment.provider)
        if not user_integration or not user_integration.encrypted_token:
            return  # No se puede monitorear sin credenciales

        try:
            raw_ciphertext = base64.b64decode(user_integration.encrypted_token.encode("utf-8"))
            decrypted_bytes = self._cipher.decrypt(EncryptedSecret(ciphertext=raw_ciphertext))
            token = decrypted_bytes.decode("utf-8")
        except Exception as exc:
            raise DeploymentAuthenticationError("Error al descifrar el token de despliegue.") from exc

        # 3. Bucle de polling periÃ³dico
        attempts = 0
        while attempts < cmd.max_attempts:
            status, public_url, logs_or_error = await self._deployment_client.get_service_status(
                token=token,
                service_id=str(deployment.service_id),
            )

            # Detectar cambios de estado o URL
            has_changed = (
                status != deployment.status
                or public_url != deployment.public_url
                or (status == DeploymentStatus.FAILED and logs_or_error != deployment.error_message)
            )

            if has_changed:
                deployment = replace(
                    deployment,
                    status=status,
                    public_url=public_url if public_url else deployment.public_url,
                    build_logs_url=logs_or_error if status == DeploymentStatus.FAILED else deployment.build_logs_url,
                    error_message=logs_or_error if status == DeploymentStatus.FAILED else None,
                )
                await self._project_deployment_repo.save(deployment)

            # Salir si el estado es terminal
            if status in (DeploymentStatus.PUBLISHED, DeploymentStatus.FAILED):
                break

            await asyncio.sleep(cmd.delay_seconds)
            attempts += 1
