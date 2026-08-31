from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime

from kosmo.contracts.auth.principal import Principal
from kosmo.contracts.auth.secrets import EncryptedSecret, SecretCipher
from kosmo.contracts.integrations.deployment import (
    DeploymentAccountNotLinkedError,
    DeploymentAuthenticationError,
    DeploymentProvider,
    DeploymentProviderPort,
    DeploymentRepositoryMissingError,
    DeploymentStatus,
    EnvironmentVariable,
    PortSpec,
    ProjectDeployment,
    ProjectDeploymentRepository,
    UserDeploymentIntegrationRepository,
    VolumeConfig,
)
from kosmo.contracts.integrations.github import (
    GitHubSyncStatus,
    ProjectGitHubIntegrationRepository,
)
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.telemetry import traced


@dataclass(frozen=True, slots=True)
class OrchestrateCloudDeploymentCommand:
    project_id: ProjectId
    provider: DeploymentProvider = DeploymentProvider.RAILWAY
    service_name: str | None = None
    environment_variables: dict[str, str] | None = None


OrquestarDespliegueNubeCommand = OrchestrateCloudDeploymentCommand
DeployRailwayCommand = OrchestrateCloudDeploymentCommand


class OrchestrateCloudDeploymentUseCase:
    """Caso de uso para orquestar la creación, configuración y disparo del despliegue en la nube."""

    def __init__(
        self,
        project_deployment_repo: ProjectDeploymentRepository,
        user_deployment_repo: UserDeploymentIntegrationRepository,
        project_github_repo: ProjectGitHubIntegrationRepository,
        deployment_client: DeploymentProviderPort,
        cipher: SecretCipher,
    ) -> None:
        self._project_deployment_repo = project_deployment_repo
        self._user_deployment_repo = user_deployment_repo
        self._project_github_repo = project_github_repo
        self._deployment_client = deployment_client
        self._cipher = cipher

    @traced("deployment.orchestrate")
    async def execute(
        self,
        principal: Principal,
        cmd: OrchestrateCloudDeploymentCommand,
    ) -> ProjectDeployment:
        # 1. Validar vinculación de la cuenta de despliegue del usuario
        user_integration = await self._user_deployment_repo.get_by_user_id(UserId(principal.subject), cmd.provider)
        if not user_integration or not user_integration.encrypted_token:
            raise DeploymentAccountNotLinkedError(
                f"La cuenta de {cmd.provider.value.capitalize()} no está vinculada. "
                "Debes conectar tu cuenta antes de iniciar el despliegue."
            )

        # 2. Descifrar credenciales
        try:
            raw_ciphertext = base64.b64decode(user_integration.encrypted_token.encode("utf-8"))
            decrypted_bytes = self._cipher.decrypt(EncryptedSecret(ciphertext=raw_ciphertext))
            token = decrypted_bytes.decode("utf-8")
        except Exception as exc:
            raise DeploymentAuthenticationError("Error al descifrar el token de despliegue del usuario.") from exc

        # 3. Validar precondición de repositorio GitHub remoto
        github_integration = await self._project_github_repo.get_by_project_id(cmd.project_id)
        if (
            not github_integration
            or not github_integration.repo_url
            or github_integration.sync_status == GitHubSyncStatus.NOT_CREATED
        ):
            raise DeploymentRepositoryMissingError(
                "El proyecto no cuenta con un repositorio remoto de GitHub sincronizado. "
                "Debes sincronizar el código con GitHub antes de publicar en la nube."
            )

        # 4. Configurar variables de entorno predeterminadas y personalizadas
        default_env_vars = [
            EnvironmentVariable(key="NODE_ENV", value="production", is_secret=False),
            EnvironmentVariable(key="PORT", value="3000", is_secret=False),
            EnvironmentVariable(key="DATABASE_URL", value="file:/data/db.sqlite", is_secret=False),
        ]
        custom_env_vars: list[EnvironmentVariable] = []
        if cmd.environment_variables:
            for k, v in cmd.environment_variables.items():
                if k not in {"NODE_ENV", "PORT", "DATABASE_URL"}:
                    custom_env_vars.append(EnvironmentVariable(key=k, value=v, is_secret=False))
        all_env_vars = default_env_vars + custom_env_vars

        volume_config = VolumeConfig(mount_path="/data", size_mb=512)
        port_spec = PortSpec(port=3000, protocol="http")

        # 5. Crear o reutilizar servicio remoto
        existing_deployment = await self._project_deployment_repo.get_by_project_id(cmd.project_id)
        now = datetime.now(UTC)

        if existing_deployment and existing_deployment.service_id:
            service_id = existing_deployment.service_id
        else:
            service_id = await self._deployment_client.create_service(
                token=token,
                repo_url=github_integration.repo_url,
                env_vars=all_env_vars,
                ports=[port_spec],
            )

        # 6. Aprovisionar volumen persistente SQLite y disparar construcción
        await self._deployment_client.configure_volume(
            token=token,
            service_id=service_id,
            volume=volume_config,
        )
        await self._deployment_client.trigger_deployment(
            token=token,
            service_id=service_id,
        )

        # 7. Actualizar y persistir el estado de despliegue del proyecto
        deployment = ProjectDeployment(
            project_id=cmd.project_id,
            provider=cmd.provider,
            service_id=service_id,
            public_url=existing_deployment.public_url if existing_deployment else None,
            status=DeploymentStatus.BUILDING,
            build_logs_url=existing_deployment.build_logs_url if existing_deployment else None,
            last_deployed_at=now,
            error_message=None,
            volumes=(volume_config,),
            ports=(port_spec,),
            env_vars=tuple(all_env_vars),
            created_at=existing_deployment.created_at if existing_deployment else now,
            updated_at=now,
        )
        await self._project_deployment_repo.save(deployment)

        return deployment


OrquestarDespliegueNubeUseCase = OrchestrateCloudDeploymentUseCase
DeployRailwayUseCase = OrchestrateCloudDeploymentUseCase
